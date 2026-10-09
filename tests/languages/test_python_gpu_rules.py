from typing import TYPE_CHECKING, cast

import pytest

from mcmr.domain.contracts import RuleContract
from mcmr.facts import CallFact, FunctionFact, SyntaxFact
from mcmr.plugins import RepositoryTables
from mcmr.rules.python import (
    blocking_raw_memory_operation_in_stream_scope,
    conditional_block_barrier,
    default_stream_numba_kernel_launch,
    device_wide_numba_synchronization_in_stream_scope,
    device_wide_synchronization_in_stream_scope,
    direct_cuda_core_lifecycle_construction,
    dynamic_kernel_array_shape,
    kernel_return_value,
    legacy_default_stream_launch,
    synchronous_transfer_in_numba_stream_scope,
    unguarded_grid_index,
)
from mcmr.table import AnalysisSession

from ..support import written

if TYPE_CHECKING:
    from mcmr.query import RuleQuery


_NUMBA = """from cuda.bindings import driver, runtime
from cuda.core import Context, Device, LEGACY_DEFAULT_STREAM, LaunchConfig, Stream, launch
from numba import cuda, float32


@cuda.jit
def unsafe_kernel(values, width):
    position = cuda.grid(1)
    cuda.shared.array(width * 2, float32)
    return values[position]


@cuda.jit
def guarded_kernel(values, width):
    position = cuda.grid(1)
    if position < width:
        cuda.syncthreads()
        values[position] = 0
    return


@cuda.jit(device=True)
def device_function(value):
    return value


def numba_host(values):
    stream = cuda.stream()
    unsafe_kernel[1, 32](values, 32)
    guarded_kernel[1, 32, stream](values, 32)
    values.copy_to_host()
    values.copy_to_host(stream=stream)
    cuda.synchronize()
    stream.synchronize()
    mapping = {}
    mapping[1, 32](values)


def cuda_python_host(values):
    Context()
    Stream()
    device = Device()
    stream = device.create_stream()
    launch(LEGACY_DEFAULT_STREAM, LaunchConfig(grid=1, block=32), unsafe_kernel, values)
    launch(stream, LaunchConfig(grid=1, block=32), unsafe_kernel, values)
    runtime.cudaDeviceSynchronize()
    driver.cuCtxSynchronize()
    runtime.cudaMemcpy(values, values, 1, 0)
    driver.cuMemAlloc(1)
    runtime.cudaMemcpyAsync(values, values, 1, 0, stream.handle)
"""

_TYPES = "from patos.cuda.typed import Constant, Per, Struct, cuda, device, i32, kernel\n"

_PATOS = """from numba import cuda as numba_cuda

from ..types import Constant, Per, Struct, cuda, device, i32, kernel


@kernel
def returning(values: i32[int]) -> None:
    return values[cuda.grid(1)]


@device
def clamp(value: i32, low: i32) -> i32:
    return max(value, low)


@device
def staged(values: i32[int], width: i32) -> None:
    tile = cuda.local.array(width, i32)
    if width:
        cuda.syncthreads()
    values[0] = tile[0]


class Merger(Struct):
    width: Constant[int]
    count: i32

    @device
    def gather(self, at: i32) -> i32:
        held = cuda.local.array(self.width * 2, i32)
        spill = cuda.local.array(self.count, i32)
        return held[at] + spill[at]

    @device
    def settle(self, values: i32[int]) -> None:
        if self.width > 1:
            cuda.syncthreads()
        if self.count:
            cuda.syncthreads()

    @kernel(per=Per.WARP, threads=256, strided=True)
    def merge(self, out: i32[int]) -> None:
        slot = cuda.grid(1)
        out[slot] = self.gather(slot)


def host(values, merger: Merger):
    stream = numba_cuda.stream()
    returning[values.size](values)
    merger.merge[values.size](values)
    return stream
"""


# A project of its own writes `cuda.jit`, `kernel`, and `device`, none of them from Numba or
# patos, so every rule here must read this module as the ordinary host code it is.
_DECOY = """from tasks import device, kernel

from . import cuda


@cuda.jit
def own_jit(values, width):
    tile = cuda.shared.array(width, int)
    if width:
        cuda.syncthreads()
    return tile


@kernel
def own_kernel(values):
    slot = cuda.grid(1)
    return values[slot]


@device
def own_device(values, width):
    if width:
        cuda.syncthreads()
    return cuda.local.array(width, int)
"""


@pytest.fixture(scope="module")
def gpu_tables(tmp_path_factory: pytest.TempPathFactory) -> RepositoryTables:
    """Parse one Python corpus covering unsafe and accepted GPU API forms.

    The `pkg` package writes its device code in the patos.cuda dialect the way cutok does, its
    decorators imported relatively from a module that re-exports `patos.cuda.typed`. Its `decoy`
    module writes the same decorator names from a module of the project's own.
    """
    root = written(
        tmp_path_factory.mktemp("python-gpu-rules"),
        {
            "gpu.py": _NUMBA,
            "pkg/__init__.py": "",
            "pkg/stage/__init__.py": "",
            "pkg/types.py": _TYPES,
            "pkg/stage/kernels.py": _PATOS,
            "pkg/cuda.py": "def jit(function):\n    return function\n",
            "pkg/decoy.py": _DECOY,
        },
    )
    session = AnalysisSession(
        root,
        suffixes=[".py"],
        typed_families=[CallFact, FunctionFact, SyntaxFact],
    )
    tables = RepositoryTables()
    tables.add(session.call_tables())
    tables.add(session.function_tables())
    tables.add(session.syntax_tables())
    return tables


def count(rule: RuleContract, tables: RepositoryTables) -> int:
    """Return the total count from one table-native GPU rule invocation."""
    query = cast("RuleQuery", rule.invoke(tables, settings={}, dependencies={}))
    value = query.values.collect().get_column("integer_value").drop_nulls().sum()
    if not isinstance(value, int):
        raise TypeError("a GPU rule returned no integer count")
    return value


@pytest.mark.parametrize(
    ("rule", "expected"),
    [
        (kernel_return_value, 2),
        (conditional_block_barrier, 3),
        (unguarded_grid_index, 2),
        (dynamic_kernel_array_shape, 3),
        (synchronous_transfer_in_numba_stream_scope, 1),
        (default_stream_numba_kernel_launch, 1),
        (device_wide_numba_synchronization_in_stream_scope, 1),
        (direct_cuda_core_lifecycle_construction, 2),
        (legacy_default_stream_launch, 1),
        (device_wide_synchronization_in_stream_scope, 2),
        (blocking_raw_memory_operation_in_stream_scope, 2),
    ],
)
def test_python_gpu_rule_cases(
    rule: RuleContract,
    expected: int,
    gpu_tables: RepositoryTables,
) -> None:
    """Each GPU rule distinguishes its unsafe form from the accepted neighboring form."""
    assert count(rule, gpu_tables) == expected

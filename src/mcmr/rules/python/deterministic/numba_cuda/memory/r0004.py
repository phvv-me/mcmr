import polars as pl

from ...... import rule
from ......facts import CallFact, FunctionFact, SyntaxFact
from ......query import CountQuery
from ......table import CallRelation, FunctionRelation, Table
from ...gpu_relations import call_rows, compiled_functions, counted_calls, record_constants

# Inside compiled device code `cuda` can only be Numba's, however a module re-exported it.
_ALLOCATORS = r"(?:^|\.)cuda\.(?:local|shared)\.array$"


@rule("PY-NUMB0004")
def dynamic_kernel_array_shape(
    subject: Table[CallFact],
    *,
    functions: Table[FunctionFact],
    declarations: Table[SyntaxFact],
) -> CountQuery:
    """Count local or shared arrays whose shape comes from a kernel parameter.

    Definition
    ----------
    Report `cuda.local.array` and `cuda.shared.array` calls whose shape argument reads a parameter
    of the surrounding kernel or device function, whether Numba's `cuda.jit` or patos.cuda's
    `kernel`, `device`, and `ptx` compiled it. These arrays require a simple compile-time constant
    shape. A launch-time parameter cannot satisfy that contract. A record method's `self` is such a
    parameter too, since a launch passes the record, except for the fields the record declares
    `Constant[...]`, which are part of its device type and so compile-time literals.

    Evidence
    --------
    Each finding identifies the allocation call, kernel, and dynamic shape parameter. The value is
    the number of kernel arrays with parameter-dependent shapes.

    Exceptions
    ----------
    Literal shapes, names bound to module constants, and a record's `Constant[...]` fields are
    accepted. Dynamic shared memory passed through the launch configuration is a different
    mechanism and does not call `shared.array` with a parameter shape. `cuda` re-exported through
    another module, as patos.cuda re-exports Numba's, names the same allocator.

    Examples
    --------
    Bad
    ~~~
    .. code-block:: python

       @cuda.jit
       def reduce(values, width):
           tile = cuda.shared.array(width, float32)

    Good
    ~~~~
    .. code-block:: python

       TILE_WIDTH = 256

       @cuda.jit
       def reduce(values):
           tile = cuda.shared.array(TILE_WIDTH, float32)

       class Merger(Struct):
           width: Constant[int]

           @device
           def gather(self, at: i32) -> i64:
               held = cuda.local.array(self.width, i64)

    References
    ----------
    Cites "Numba CUDA documentation", memory management and local memory
    https://nvidia.github.io/numba-cuda/user/memory.html#local-memory
    Cites "Numba CUDA documentation", CUDA Kernel API and memory management
    https://nvidia.github.io/numba-cuda/reference/kernel.html#memory-management
    """
    parameters = functions.lazy(FunctionRelation.PARAMETERS).join(
        compiled_functions(functions, "kernel", "device"),
        left_on="function_id",
        right_on="entity_id",
        how="inner",
    )
    shapes = (
        subject.lazy(CallRelation.EXPRESSIONS)
        .filter(
            (pl.col("root_relation") == "argument")
            & (pl.col("root_ordinal") == 0)
            & (pl.col("depth") == 0)
        )
        .select("call_id", pl.col("text").alias("shape"))
    )
    constants = (
        record_constants(declarations, functions)
        .group_by(pl.col("entity_id").alias("function_id"))
        .agg(pl.col("field").alias("constants"))
    )
    read = pl.concat_str(pl.lit(r"\b"), pl.col("name"), pl.lit(r"\b"))
    field_read = pl.concat_str(pl.lit(r"\b"), pl.col("name"), pl.lit(r"\.\w+"))
    fields = (
        pl.col("shape")
        .str.extract_all(field_read)
        .list.eval(pl.element().str.split(".").list.get(1))
    )
    runtime_field = (
        pl.col("shape").str.count_matches(read) > pl.col("shape").str.count_matches(field_read)
    ) | (fields.list.set_difference(pl.col("constants")).list.len() > 0)
    selected = (
        call_rows(subject)
        .filter(pl.col("qualified_name").str.contains(_ALLOCATORS))
        .join(shapes, on="call_id", how="inner")
        .join(parameters, left_on="node_path", right_on="path", how="inner")
        .filter(
            (pl.col("node_start_line") >= pl.col("definition_start_line"))
            & (pl.col("node_end_line") <= pl.col("definition_end_line"))
            & pl.col("shape").str.contains(read)
        )
        .join(constants, on="function_id", how="left")
        .with_columns(pl.col("constants").fill_null(pl.lit([], dtype=pl.List(pl.String))))
        .filter(~pl.col("is_receiver") | runtime_field)
    )
    return counted_calls(
        subject,
        selected,
        pl.concat_str(
            pl.lit("`"),
            pl.col("qualified_name"),
            pl.lit("` takes its shape `"),
            pl.col("shape"),
            pl.lit("` from parameter `"),
            pl.col("name"),
            pl.lit("`, which a launch sets at run time"),
        ),
        "dynamic kernel array shape",
    )

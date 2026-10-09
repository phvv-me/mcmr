use super::{Value, extracted, json};

fn device_roles(sources: &[(&str, &str)]) -> Vec<(Value, Value)> {
    extracted(sources)
        .remove("FunctionFact")
        .unwrap_or_default()
        .into_iter()
        .map(|fact| (fact["name"].clone(), fact["device_role"].clone()))
        .collect()
}

#[test]
fn a_decorator_re_exported_through_project_modules_keeps_its_device_role() {
    let roles = device_roles(&[
        ("cutoken/__init__.py", "from .types import kernel\n"),
        (
            "cutoken/types.py",
            "from patos.cuda.typed import Struct, cuda, device, kernel\n",
        ),
        ("cutoken/stage/__init__.py", ""),
        (
            "cutoken/stage/kernels.py",
            concat!(
                "from .. import kernel as packaged\n",
                "from ..types import Struct, cuda, device, kernel\n\n\n",
                "@device\n",
                "def clamp(value):\n",
                "    return value\n\n\n",
                "@packaged(threads=256)\n",
                "def fill(values):\n",
                "    values[cuda.grid(1)] = 0\n\n\n",
                "class Merger(Struct):\n",
                "    @kernel\n",
                "    def merge(self, out):\n",
                "        out[0] = 0\n\n\n",
                "def host(values):\n",
                "    fill[values.size](values)\n",
            ),
        ),
    ]);

    assert_eq!(
        roles,
        [
            (json!("clamp"), json!("device")),
            (json!("fill"), json!("kernel")),
            (json!("merge"), json!("kernel")),
            (json!("host"), json!("")),
        ]
    );
}

#[test]
fn a_project_decorator_defined_rather_than_imported_marks_nothing() {
    let roles = device_roles(&[
        ("tasks/__init__.py", ""),
        (
            "tasks/types.py",
            "def kernel(function):\n    return function\n",
        ),
        (
            "tasks/jobs.py",
            "from .types import kernel\n\n\n@kernel\ndef scheduled(job):\n    return job\n",
        ),
        (
            "tasks/cycle.py",
            "from .loop import kernel\n\n\n@kernel\ndef looped(job):\n    return job\n",
        ),
        ("tasks/loop.py", "from .cycle import kernel\n"),
    ]);

    assert_eq!(
        roles,
        [
            (json!("kernel"), json!("")),
            (json!("scheduled"), json!("")),
            (json!("looped"), json!("")),
        ]
    );
}

#[test]
fn a_project_module_named_cuda_marks_nothing_unless_it_re_exports_numba() {
    let roles = device_roles(&[
        ("accel/__init__.py", ""),
        ("accel/cuda.py", "def jit(function):\n    return function\n"),
        ("accel/gpu.py", "from numba import cuda\n"),
        (
            "accel/use.py",
            concat!(
                "from . import cuda\n",
                "from .cuda import jit\n",
                "from .gpu import cuda as numba_cuda\n\n\n",
                "@cuda.jit\n",
                "def own(values):\n",
                "    values[0] = 0\n\n\n",
                "@jit\n",
                "def imported(values):\n",
                "    values[0] = 0\n\n\n",
                "@numba_cuda.jit\n",
                "def compiled(values):\n",
                "    values[0] = 0\n",
            ),
        ),
    ]);

    assert_eq!(
        roles,
        [
            (json!("jit"), json!("")),
            (json!("own"), json!("")),
            (json!("imported"), json!("")),
            (json!("compiled"), json!("kernel")),
        ]
    );
}

#[test]
fn a_star_import_binds_no_name_a_decorator_can_be_followed_through() {
    let roles = device_roles(&[
        ("pkg/__init__.py", ""),
        ("pkg/types.py", "from patos.cuda.typed import kernel\n"),
        (
            "pkg/stage.py",
            "from .types import *\n\n\n@kernel\ndef fill(values):\n    values[0] = 0\n",
        ),
    ]);

    assert_eq!(roles, [(json!("fill"), json!(""))]);
}

#[test]
fn a_re_export_under_another_name_and_a_chain_of_them_keep_the_device_role() {
    let roles = device_roles(&[
        ("pkg/__init__.py", "from .api import launch\n"),
        (
            "pkg/types.py",
            "from patos.cuda.typed import device as on_device, kernel\n",
        ),
        ("pkg/api.py", "from .types import kernel as launch\n"),
        (
            "pkg/stage.py",
            concat!(
                "from . import launch\n",
                "from .types import on_device\n\n\n",
                "@launch\n",
                "def fill(values):\n",
                "    values[0] = 0\n\n\n",
                "@on_device\n",
                "def clamp(value):\n",
                "    return value\n",
            ),
        ),
    ]);

    assert_eq!(
        roles,
        [
            (json!("fill"), json!("kernel")),
            (json!("clamp"), json!("device")),
        ]
    );
}

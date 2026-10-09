use super::*;

fn device_roles<const N: usize>(source: &str, names: [&str; N]) -> [String; N] {
    names.map(|name| {
        function_named(source, FactName(name))["device_role"]
            .as_str()
            .expect("FunctionFact.device_role is text")
            .to_string()
    })
}

#[test]
fn cuda_jit_marks_a_kernel_and_a_device_function_in_every_spelling_it_takes() {
    let source = concat!(
        "from numba import cuda\n",
        "from numba.cuda import jit\n\n\n",
        "@cuda.jit\n",
        "def add(x, y, out):\n",
        "    position = cuda.grid(1)\n",
        "    out[position] = x[position] + y[position]\n\n\n",
        "@cuda.jit(device=True)\n",
        "def scale(value, factor):\n",
        "    return value * factor\n\n\n",
        "@numba.cuda.jit(device = True, inline=True)\n",
        "def add_one(value):\n",
        "    return value + 1\n\n\n",
        "@jit\n",
        "def double(value):\n",
        "    return value * 2\n\n\n",
        "def plain(value):\n",
        "    return value\n",
    );

    assert_eq!(
        device_roles(source, ["add", "scale", "add_one", "double", "plain"]),
        ["kernel", "device", "device", "kernel", ""]
    );
}

#[test]
fn a_bare_jit_only_counts_when_this_file_imported_it_from_numba_cuda() {
    let source = concat!(
        "from jax import jit\n",
        "from numba import jit as cpu\n\n\n",
        "@jit\n",
        "def transform(value):\n",
        "    return value\n\n\n",
        "@cpu\n",
        "def host(value):\n",
        "    return value\n",
    );

    assert_eq!(device_roles(source, ["transform", "host"]), ["", ""]);
}

#[test]
fn patos_kernel_device_and_ptx_mark_their_roles_in_every_spelling_they_take() {
    let source = concat!(
        "import patos.cuda.typed as typed\n",
        "from patos.cuda.typed import Per, Struct, device, kernel, ptx\n",
        "from patos.cuda.typed.kernels import kernel as launched\n\n\n",
        "@kernel\n",
        "def fill(values):\n",
        "    values[0] = 0\n\n\n",
        "@kernel(per=Per.WARP, threads=256, strided=True)\n",
        "def sweep(values):\n",
        "    values[0] = 0\n\n\n",
        "@typed.kernel\n",
        "def qualified(values):\n",
        "    values[0] = 0\n\n\n",
        "@launched\n",
        "def renamed(values):\n",
        "    values[0] = 0\n\n\n",
        "@device\n",
        "def clamp(value):\n",
        "    return value\n\n\n",
        "@device(inline=False)\n",
        "def outlined(value):\n",
        "    return value\n\n\n",
        "@ptx(\"mov.u32 $result, %laneid;\")\n",
        "def lane() -> int: ...\n\n\n",
        "class Merger(Struct):\n",
        "    @property\n",
        "    @device\n",
        "    def width(self):\n",
        "        return 1\n\n",
        "    @kernel(threads=128)\n",
        "    def merge(self, out):\n",
        "        out[0] = self.width\n\n\n",
        "def host(values):\n",
        "    fill[values.size](values)\n",
    );

    assert_eq!(
        device_roles(
            source,
            [
                "fill",
                "sweep",
                "qualified",
                "renamed",
                "clamp",
                "outlined",
                "lane",
                "width",
                "merge",
                "host",
            ],
        ),
        [
            "kernel", "kernel", "kernel", "kernel", "device", "device", "device", "device",
            "kernel", "",
        ]
    );
}

#[test]
fn a_same_named_decorator_from_another_library_marks_nothing() {
    let source = concat!(
        "from tasks import kernel\n",
        "from torch import device\n",
        "from myapp import cuda\n",
        "from myapp.cuda import jit\n\n\n",
        "@kernel\n",
        "def scheduled(job):\n",
        "    return job\n\n\n",
        "@device\n",
        "def placed(tensor):\n",
        "    return tensor\n\n\n",
        "@cuda.jit\n",
        "def compiled(value):\n",
        "    return value\n\n\n",
        "@jit\n",
        "def traced(value):\n",
        "    return value\n",
    );

    assert_eq!(
        device_roles(source, ["scheduled", "placed", "compiled", "traced"]),
        ["", "", "", ""]
    );
}

#[test]
fn a_relative_import_resolves_against_the_importing_module() {
    let source = concat!(
        "from ..typed import kernel\n",
        "from .types import device\n\n\n",
        "@kernel\n",
        "def fill(values):\n",
        "    values[0] = 0\n\n\n",
        "@device\n",
        "def clamp(value):\n",
        "    return value\n",
    );
    let roles = facts_for_path(
        RelativePath("patos/cuda/primitives/warp.py"),
        source,
        FactFamily("FunctionFact"),
    )
    .into_iter()
    .map(|fact| (fact["name"].clone(), fact["device_role"].clone()))
    .collect::<Vec<_>>();

    assert_eq!(
        roles,
        [
            (json!("fill"), json!("kernel")),
            (json!("clamp"), json!(""))
        ]
    );
}

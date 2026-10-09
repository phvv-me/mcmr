/// What a CUDA JIT compiles one callable as, read from the decorators it wears.
///
/// Numba's `cuda.jit` compiles a kernel, or a device function when it is called with
/// `device=True`. `patos.cuda.typed` states the same two roles as `kernel` and `device`, and its
/// `ptx` declares a device function written as one PTX block. Every decorator is read through the
/// absolute name it binds, so an alias or a re-export names the same role while a same-named
/// decorator from another library names none.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum DeviceRole {
    #[default]
    Host,
    Kernel,
    Device,
}

impl DeviceRole {
    /// Read the role from decorator texts, `resolve` naming what each applied name stands for.
    pub(crate) fn of(decorators: &[String], resolve: impl Fn(&str) -> String) -> Self {
        decorators
            .iter()
            .map(|decorator| Self::worn(decorator, &resolve))
            .find(|role| *role != Self::Host)
            .unwrap_or_default()
    }

    /// The spelling a fact states this role in, empty for host code.
    pub(crate) fn as_str(self) -> &'static str {
        match self {
            Self::Host => "",
            Self::Kernel => "kernel",
            Self::Device => "device",
        }
    }

    /// Return the role one decorator compiles with, `resolve` naming what its applied name stands
    /// for.
    fn worn(decorator: &str, resolve: &impl Fn(&str) -> String) -> Self {
        let target = resolve(decorator.split('(').next().unwrap_or(decorator).trim());
        let (module, name) = target.rsplit_once('.').unwrap_or(("", target.as_str()));
        if name == "jit" && matches!(module, "cuda" | "numba.cuda" | "patos.cuda.typed.cuda") {
            let written: String = decorator.split_whitespace().collect();
            return match written.contains("device=True") {
                true => Self::Device,
                false => Self::Kernel,
            };
        }
        if module != "patos.cuda.typed" && !module.starts_with("patos.cuda.typed.") {
            return Self::Host;
        }
        match name {
            "kernel" => Self::Kernel,
            "device" | "ptx" => Self::Device,
            _ => Self::Host,
        }
    }
}

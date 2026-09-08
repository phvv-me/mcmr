/// One source file the kernel read once for every family that needs it.
pub struct Document {
    pub relative: String,
    pub source: String,
}

impl Document {
    pub fn is_package_initializer(&self) -> bool {
        self.relative.rsplit('/').next() == Some("__init__.py")
    }
}

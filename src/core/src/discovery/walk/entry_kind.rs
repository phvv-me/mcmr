/// Whether one path names a directory, which decides how an ignore pattern is matched against it.
#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) enum EntryKind {
    Directory,
    File,
}

impl EntryKind {
    pub(super) fn is_directory(self) -> bool {
        self == Self::Directory
    }
}

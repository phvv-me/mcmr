use serde::Serialize;

/// How widely one declaration reaches, in the one vocabulary every frontend fills.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Visibility {
    Public,
    Protected,
    Internal,
    Private,
}

impl Visibility {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Public => "public",
            Self::Protected => "protected",
            Self::Internal => "internal",
            Self::Private => "private",
        }
    }

    /// Return whichever of two visibilities reaches less far.
    ///
    /// Two files may declare one node, and the graph keeps the narrower claim so a rule never
    /// reads a symbol as more widely reachable than the strictest declaration allows.
    pub fn narrower(self, other: Self) -> Self {
        if self.reach() <= other.reach() {
            self
        } else {
            other
        }
    }

    /// How far one visibility reaches, ordered from the narrowest outward.
    fn reach(self) -> u8 {
        match self {
            Self::Private => 0,
            Self::Internal => 1,
            Self::Protected => 2,
            Self::Public => 3,
        }
    }
}

import re

_PLATFORM = "mcmr"


def platform_key(*parts: str) -> str:
    """Return one identity key under the platform every MCMR entity is published on.

    Every identity MCMR mints starts with the platform, so a catalog holding several tools keeps
    them apart on sight and a search for the platform finds the whole of what this one wrote.
    """
    return "-".join((_PLATFORM, *parts))


def slug(name: str) -> str:
    """Return the one lowercase hyphenated key any human name always resolves to."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

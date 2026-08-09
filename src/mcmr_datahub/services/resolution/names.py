import re
from functools import cached_property

from patos import FrozenModel

_DATASET_URN_PREFIX = "urn:li:dataset:("
_IDENTIFIER = re.compile(r"[^\W\d_]\w*")


class AssetName(FrozenModel):
    """Judge whether one spelling a source literal states can name a data asset at all.

    Every string literal in a repository reaches this class, and most of them are prose, log
    templates, or code in another language. A SQL parser reads `delete the annotation` as a table
    named `the`, and a half built URN constant looks like an asset to anything matching on a
    prefix. A spelling therefore counts as a mention only once it carries its own evidence of
    being one, which is either a complete canonical dataset URN or a dotted name stating both a
    container and an asset. A bare word carries neither.
    """

    text: str

    @property
    def dataset(self) -> str:
        """Return the dataset name a complete canonical URN states, empty when it states none."""
        return self.urn_parts[1] if self.urn_parts else ""

    @property
    def is_dataset_urn(self) -> bool:
        """Whether the spelling is one complete canonical DataHub dataset URN."""
        return bool(self.urn_parts)

    @property
    def is_qualified(self) -> bool:
        """Whether the spelling is a dotted identifier naming both a container and an asset."""
        parts = self.text.split(".")
        return len(parts) > 1 and all(_IDENTIFIER.fullmatch(part) for part in parts)

    @property
    def opens_dataset_urn(self) -> bool:
        """Whether the spelling starts a dataset URN, whether or not it finishes one."""
        return self.text.startswith(_DATASET_URN_PREFIX)

    @cached_property
    def urn_parts(self) -> list[str]:
        """Return the platform, name, and environment one complete dataset URN states."""
        if not self.opens_dataset_urn:
            return []
        parts = self._top_level(self._enclosed(self.text[len(_DATASET_URN_PREFIX) - 1 :]))
        return parts if len(parts) == 3 and all(parts) else []

    @staticmethod
    def _enclosed(text: str) -> str:
        """Return what one leading parenthesis encloses when it closes at the very end."""
        depth = 0
        for index, character in enumerate(text):
            depth += (character == "(") - (character == ")")
            if depth == 0:
                return text[1:index] if index == len(text) - 1 else ""
        return ""

    @staticmethod
    def _top_level(enclosed: str) -> list[str]:
        """Split one URN body on the commas that no nested parenthesis holds."""
        parts: list[str] = []
        depth = 0
        current: list[str] = []
        for character in enclosed:
            depth += (character == "(") - (character == ")")
            if character == "," and depth == 0:
                parts.append("".join(current))
                current = []
                continue
            current.append(character)
        parts.append("".join(current))
        return parts

import json
import re
from collections import Counter
from functools import cached_property

from patos import FrozenModel
from pydantic import JsonValue
from tron import stringify


class TronDocument(FrozenModel):
    """Render shared shapes with TRON and large source text with safe Markdown blocks."""

    document: dict[str, JsonValue]

    @cached_property
    def fence(self) -> str:
        """Choose one Markdown fence no literal evidence can close."""
        longest = max(
            (
                max((len(match.group()) for match in re.finditer(r"`+", value)), default=0)
                for value in self.text_counts
            ),
            default=0,
        )
        return "`" * max(3, longest + 1)

    @cached_property
    def text_counts(self) -> Counter[str]:
        """Count string values without treating mapping keys as evidence text."""
        counts: Counter[str] = Counter()
        self._count_text(self.document, counts)
        return counts

    @cached_property
    def texts(self) -> dict[str, str]:
        """Reference repeated or escaped text only when a literal block is smaller."""
        texts: dict[str, str] = {}
        used = set(self.text_counts)
        for value, count in self.text_counts.items():
            index = len(texts)
            alias = f"@{index}"
            while alias in used:
                index += 1
                alias = f"@{index}"
            direct = count * len(self._quoted(value).encode())
            block = (
                count * len(self._quoted(alias).encode())
                + len(alias.encode())
                + len(value.encode())
                + 2 * len(self.fence.encode())
                + 4
            )
            if (count > 1 or "\n" in value) and block < direct:
                texts[alias] = value
                used.add(alias)
        return texts

    def render(self) -> str:
        """Render literal text bindings followed by one lossless TRON document."""
        lines: list[str] = []
        if self.texts:
            lines.append("Text blocks")
            for alias, value in self.texts.items():
                lines.extend((alias, self.fence, value, self.fence))
        lines.extend(("TRON", stringify(self._replaced(self.document))))
        return "\n".join(lines)

    @staticmethod
    def _quoted(value: str) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def _count_text(cls, value: JsonValue, counts: Counter[str]) -> None:
        match value:
            case dict() as mapping:
                for item in mapping.values():
                    cls._count_text(item, counts)
            case list() as items:
                for item in items:
                    cls._count_text(item, counts)
            case str() as text:
                counts[text] += 1

    def _replaced(self, value: JsonValue) -> JsonValue:
        match value:
            case dict() as mapping:
                return {key: self._replaced(item) for key, item in mapping.items()}
            case list() as items:
                return [self._replaced(item) for item in items]
            case str() as text:
                return next((alias for alias, held in self.texts.items() if held == text), text)
            case _:
                return value

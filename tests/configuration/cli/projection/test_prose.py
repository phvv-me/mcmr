import sys
from pathlib import Path

import pytest

from mcmr.commands import cli


def test_cli_reports_a_native_analysis_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An invalid owner boundary exits with a readable error from the real analysis session."""
    monkeypatch.setattr(sys, "argv", ["mcmr", "check", str(tmp_path), "--boundaries", "missing"])

    with pytest.raises(SystemExit) as stopped:
        cli.main()

    output = capsys.readouterr().out
    assert (stopped.value.code, "Analysis failed:" in output, "owner boundary" in output) == (
        2,
        True,
        True,
    )


def test_prose_exports_narrative_in_document_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Includes follow reading order while cells, floats, and bibliography stay out of prose."""
    (tmp_path / "paper.tex").write_text(
        r"""\documentclass{article}\begin{document}
First sentence. Second sentence.

\input{z-first}\input{a-last}
\begin{tabular}{l}Hidden cell.\end{tabular}
\begin{figure}Hidden float.\caption{Hidden caption.}\end{figure}
\begin{thebibliography}{1}\bibitem{ref}Hidden reference.\end{thebibliography}
\end{document}"""
    )
    (tmp_path / "z-first.tex").write_text("Included first.\n\n")
    (tmp_path / "a-last.tex").write_text("Included last.\n\n")
    monkeypatch.setattr(sys, "argv", ["mcmr", "prose", str(tmp_path)])

    with pytest.raises(SystemExit, match="^0$"):
        cli.main()

    assert capsys.readouterr().out == (
        "First sentence. Second sentence.\n\nIncluded first.\n\nIncluded last.\n\n"
    )


def test_prose_exports_typst_paragraphs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Typst prose shares the paragraph export and preserves literal bracketed text."""
    (tmp_path / "paper.typ").write_text("First [bold] sentence.\n\nSecond paragraph.\n")
    monkeypatch.setattr(sys, "argv", ["mcmr", "prose", str(tmp_path)])

    with pytest.raises(SystemExit, match="^0$"):
        cli.main()

    assert capsys.readouterr().out == "First [bold] sentence.\n\nSecond paragraph.\n\n"


def test_prose_without_manuscripts_prints_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty repository exports an empty narrative without an error or status banner."""
    monkeypatch.setattr(sys, "argv", ["mcmr", "prose", str(tmp_path)])

    with pytest.raises(SystemExit, match="^0$"):
        cli.main()

    assert capsys.readouterr().out == ""

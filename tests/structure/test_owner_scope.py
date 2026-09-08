import json
from pathlib import Path

import pytest

from mcmr.commands.quality import check
from mcmr.facts import InteropFact, ManuscriptFact, ModuleFact, RouteFact, SymbolReachFact
from mcmr.kernel_tables import AnalysisError
from mcmr.presentation.reports import CheckFormat
from mcmr.query import RuleQuery
from mcmr.rules.general import unreferenced_public_declaration
from mcmr.table import AnalysisSession


@pytest.fixture
def owners(tmp_path: Path) -> Path:
    for name, source in {
        "owned.py": "def used():\n    return 1\n\ndef unused():\n    return 2\n",
        "caller.py": "from owned import used\nvalue = used()\n",
        "foreign/broken.py": "def not_valid(\n",
        "foreign/Cargo.toml": "not valid TOML",
        "foreign/main.tex": "\\documentclass{article}\\begin{document}Foreign\\end{document}",
        "foreign_more/valid.py": "result = 3\n",
        "pyproject.toml": "[project]\nrequires-python = '>=3.14'\n",
        "mainboard.toml": "[tasks]\nsetup = 'sudo apt install x'\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
    return tmp_path


def test_owner_retains_unchanged_callers_and_excludes_foreign_readers(owners: Path) -> None:
    session = AnalysisSession(
        owners,
        boundaries=[Path("foreign")],
        typed_families=[ModuleFact, SymbolReachFact, ManuscriptFact],
    )
    assert session.stats.file_count == 3
    assert session.stats.parse_failure_count == 0
    assert session.table(ManuscriptFact).facts().collect().height == 0
    result = unreferenced_public_declaration.invoke_table(
        session.table(SymbolReachFact), settings={}, dependencies={}
    )
    assert isinstance(result, RuleQuery) and result.findings is not None
    messages = result.findings.rows.collect().get_column("message").to_list()
    assert len(messages) == 1 and "owned.unused" in messages[0]
    (owners / "caller.py").unlink()
    session = AnalysisSession(
        owners, boundaries=[Path("foreign")], typed_families=[SymbolReachFact]
    )
    result = unreferenced_public_declaration.invoke_table(
        session.table(SymbolReachFact), settings={}, dependencies={}
    )
    assert isinstance(result, RuleQuery) and result.findings is not None
    assert result.findings.rows.collect().height == 2


def test_root_manifest_facts_survive_without_source_modules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "foreign").mkdir()
    (tmp_path / "mainboard.toml").write_text("[tasks]\nsetup = 'sudo apt install x'\n")
    with pytest.raises(SystemExit) as stopped:
        check(
            tmp_path, boundaries=(Path("foreign"),), select="ALL-LIFE0001", format=CheckFormat.JSON
        )
    report = json.loads(capsys.readouterr().out)
    assert stopped.value.code == 1
    assert report["file_count"] == 0
    assert report["rule_execution_count"] == 1
    assert report["boundaries"] == ["foreign"]
    assert report["failures"][0]["span"]["path"] == "mainboard.toml"


@pytest.mark.parametrize(
    "boundary", [".", "..", "/tmp", "missing", "owned.py", "foreign/../foreign"]
)
def test_invalid_owner_boundary_refuses(owners: Path, boundary: str) -> None:
    with pytest.raises(AnalysisError, match="owner boundary"):
        AnalysisSession(owners, boundaries=[Path(boundary)], typed_families=[ModuleFact])


def test_boundary_cannot_use_a_symbolic_link_alias(owners: Path) -> None:
    (owners / "alias").symlink_to(owners / "foreign", target_is_directory=True)
    with pytest.raises(AnalysisError, match="symbolic-link"):
        AnalysisSession(owners, boundaries=[Path("alias")], typed_families=[ModuleFact])


def test_typescript_extends_cannot_read_another_owner(owners: Path) -> None:
    (owners / "owned.ts").write_text("export const value = 1;\n")
    (owners / "tsconfig.json").write_text('{"extends": "./foreign/base.json"}')
    (owners / "foreign/base.json").write_text("this must not be parsed")
    with pytest.raises(AnalysisError, match="crosses a nested-owner boundary"):
        AnalysisSession(owners, boundaries=[Path("foreign")], typed_families=[SymbolReachFact])


def test_owner_boundary_participates_in_analysis_identity(owners: Path) -> None:
    first = AnalysisSession(owners, boundaries=[Path("foreign")], typed_families=[ModuleFact])
    (owners / "empty").mkdir()
    second = AnalysisSession(
        owners, boundaries=[Path("foreign"), Path("empty")], typed_families=[ModuleFact]
    )
    assert first.stats.repository_fingerprint != second.stats.repository_fingerprint


def test_nested_components_and_routes_keep_only_owned_evidence(owners: Path) -> None:
    native = owners / "native"
    native.mkdir()
    (native / "Cargo.toml").write_text('[[bin]]\nname = "owned-tool"\npath = "main.rs"\n')
    (native / "main.rs").write_text("fn main() {}\n")
    (owners / "web.py").write_text('@app.get("/owned")\ndef home():\n    return 1\n')
    (owners / "foreign/web.py").write_text('@app.get("/foreign")\ndef home():\n    return 1\n')
    session = AnalysisSession(
        owners, boundaries=[Path("foreign")], typed_families=[InteropFact, RouteFact]
    )
    assert session.table(InteropFact).facts().collect().get_column("name").to_list() == [
        "owned-tool"
    ]
    assert session.table(RouteFact).records("routes").collect().get_column("path").to_list() == [
        "/owned"
    ]

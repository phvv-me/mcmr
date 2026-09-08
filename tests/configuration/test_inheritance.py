import json
from pathlib import Path

import pytest

from mcmr.commands.quality import check
from mcmr.facts import ModuleFact, ProjectConfigurationFact
from mcmr.facts import TestSuiteFact as SuiteFact
from mcmr.kernel_tables import AnalysisError
from mcmr.presentation.reports import CheckFormat
from mcmr.table import AnalysisSession


@pytest.fixture
def nested_configuration(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nrequires-python = '>=3.14'\n"
        "[tool.pytest.ini_options]\nstrict = true\naddopts = '--import-mode=importlib'\n"
    )
    (tmp_path / "broken_parent.py").write_text("def invalid(\n")
    owner = tmp_path / "hooks"
    owner.mkdir()
    (owner / "pyproject.toml").write_text("[tool.ty.environment]\nextra-paths = ['..']\n")
    (owner / "owned.py").write_text("result = 1\n")
    return owner


@pytest.mark.parametrize("rule", ["PY-TYPE0003", "PY-TEST0004", "PY-TEST0005"])
def test_tool_only_configuration_inherits_without_reading_parent_code(
    nested_configuration: Path, capsys: pytest.CaptureFixture[str], rule: str
) -> None:
    check(
        nested_configuration,
        select=rule,
        format=CheckFormat.JSON,
    )
    report = json.loads(capsys.readouterr().out)
    assert report["failures"] == []
    session = AnalysisSession(
        nested_configuration, typed_families=[ModuleFact, ProjectConfigurationFact, SuiteFact]
    )
    assert session.stats.file_count == 1 and session.stats.parse_failure_count == 0
    facts = session.table(SuiteFact).facts().collect()
    assert facts["path"].to_list() == ["pyproject.toml"]
    assert "../pyproject.toml" in str(facts["evidence"].to_list())


@pytest.mark.parametrize("rule", ["PY-TYPE0003", "PY-TEST0004", "PY-TEST0005"])
def test_local_conflicts_and_invalid_targets_remain_findings(
    nested_configuration: Path, capsys: pytest.CaptureFixture[str], rule: str
) -> None:
    (nested_configuration / "pyproject.toml").write_text(
        "[tool.ty.environment]\npython-version = '3.13'\n"
        "[tool.ruff]\ntarget-version = 'invalid'\n"
        "[tool.pytest.ini_options]\nstrict_markers = true\n"
    )
    with pytest.raises(SystemExit) as stopped:
        check(
            nested_configuration,
            select=rule,
            format=CheckFormat.JSON,
        )
    report = json.loads(capsys.readouterr().out)
    assert stopped.value.code == 1 and len(report["failures"]) == 1


def test_ancestor_change_invalidates_identity_and_bad_metadata_refuses(
    nested_configuration: Path,
) -> None:
    first = AnalysisSession(nested_configuration, typed_families=[ProjectConfigurationFact])
    parent = nested_configuration.parent / "pyproject.toml"
    parent.write_text(parent.read_text().replace(">=3.14", ">=3.15"))
    second = AnalysisSession(nested_configuration, typed_families=[ProjectConfigurationFact])
    assert first.stats.repository_fingerprint != second.stats.repository_fingerprint
    parent.write_text("[project\n")
    with pytest.raises(AnalysisError, match="not valid TOML"):
        AnalysisSession(nested_configuration, typed_families=[ProjectConfigurationFact])


def test_a_real_project_does_not_borrow_an_enclosing_declaration(
    nested_configuration: Path,
) -> None:
    (nested_configuration / "pyproject.toml").write_text("[project]\nname = 'independent'\n")
    (nested_configuration.parent / "pyproject.toml").write_text("not valid TOML")
    session = AnalysisSession(nested_configuration, typed_families=[ProjectConfigurationFact])
    facts = session.table(ProjectConfigurationFact).facts().collect()
    assert facts["python_target.project_minimum_minor"].to_list() == [None]


def test_relative_analysis_roots_read_the_same_ancestor_configuration(
    nested_configuration: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(nested_configuration)
    session = AnalysisSession(Path("."), typed_families=[ProjectConfigurationFact])
    facts = session.table(ProjectConfigurationFact).facts().collect()
    assert facts["python_target.project_minimum_minor"].to_list() == [14]

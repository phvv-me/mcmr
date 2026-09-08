from typing import TYPE_CHECKING

import pytest

from mcmr.facts import ImportBindingFact, SymbolReachFact
from mcmr.query import RuleQuery
from mcmr.rules.general import unreferenced_public_declaration
from mcmr.rules.python import relative_import_beyond_package
from mcmr.table import AnalysisSession

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(params=[False, True], ids=["parent-root", "package-root"])
def package_scan(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    package = tmp_path / "hooks"
    for name, source in {
        "__init__.py": "from .result import Result\n__all__ = ['Result']\n",
        "result.py": "class Result:\n    pass\n",
        "changes.py": "class Changes:\n    pass\n",
        "unused.py": "class Unused:\n    pass\n",
        "quality.py": "from .changes import Changes\nchanges = Changes()\n",
        "tests/__init__.py": "",
        "tests/test_quality.py": "from ..result import Result\nresult = Result()\n",
        "tests/beyond.py": "from ...outside import Missing\n",
    }.items():
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return package if request.param else tmp_path


def test_package_root_keeps_relative_depth_and_reach_evidence(package_scan: Path) -> None:
    session = AnalysisSession(
        package_scan,
        suffixes=[".py"],
        typed_families=[ImportBindingFact, SymbolReachFact],
    )
    imports = relative_import_beyond_package.invoke_table(
        session.import_binding_tables(), settings={}, dependencies={}
    )
    reach = unreferenced_public_declaration.invoke_table(
        session.table(SymbolReachFact), settings={}, dependencies={}
    )
    assert isinstance(imports, RuleQuery) and imports.findings is not None
    assert isinstance(reach, RuleQuery) and reach.findings is not None
    assert imports.values.collect().get_column("boolean_value").sum() == 1
    assert imports.findings.rows.collect().item(0, "path").endswith("tests/beyond.py")
    assert reach.values.collect().get_column("integer_value").sum() == 1
    assert "hooks.unused.Unused" in reach.findings.rows.collect().item(0, "message")

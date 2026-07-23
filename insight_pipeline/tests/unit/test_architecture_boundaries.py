"""Enforces docs/PLATFORM_ARCHITECTURE.md §1/§22: contracts and ports never
import a concrete data/plotting framework, and hypothesis_agent never
imports insight_pipeline (dependency points one way only)."""

import ast
from pathlib import Path

INSIGHT_SRC = Path(__file__).parents[2] / "src" / "insight_pipeline"
HYPOTHESIS_SRC = Path(__file__).parents[3] / "hypothesis_agent" / "src" / "hypothesis_agent"

FORBIDDEN_IN_CONTRACTS_AND_PORTS = (
    "pandas",
    "numpy",
    "scipy",
    "matplotlib",
    "plotly",
    "sqlalchemy",
    "sqlite3",
    "psycopg2",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_contracts_and_ports_never_import_data_or_plotting_frameworks():
    offenders = []
    for layer in ("contracts", "ports"):
        for path in (INSIGHT_SRC / layer).rglob("*.py"):
            for module in _imported_modules(path):
                top_level = module.split(".")[0]
                if top_level in FORBIDDEN_IN_CONTRACTS_AND_PORTS:
                    offenders.append(f"{path.relative_to(INSIGHT_SRC)} imports {module}")
    assert not offenders, "\n".join(offenders)


def test_hypothesis_agent_never_imports_insight_pipeline():
    offenders = []
    if not HYPOTHESIS_SRC.exists():
        return
    for path in HYPOTHESIS_SRC.rglob("*.py"):
        for module in _imported_modules(path):
            if module.startswith("insight_pipeline"):
                offenders.append(f"{path.relative_to(HYPOTHESIS_SRC)} imports {module}")
    assert not offenders, "\n".join(offenders)

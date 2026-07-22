"""Enforces the layering claim in docs/ARCHITECTURE.md §2: `reasoning/` and
`contracts/` must never import from `adapters/`."""

import ast
from pathlib import Path

SRC = Path(__file__).parents[2] / "src" / "hypothesis_agent"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_reasoning_and_contracts_never_import_adapters():
    offenders = []
    for layer in ("reasoning", "contracts"):
        for path in (SRC / layer).rglob("*.py"):
            for module in _imported_modules(path):
                if module.startswith("hypothesis_agent.adapters"):
                    offenders.append(f"{path.relative_to(SRC)} imports {module}")
    assert not offenders, "\n".join(offenders)

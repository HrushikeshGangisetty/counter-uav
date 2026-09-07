"""The PRD module boundaries, enforced by AST inspection of src/pod_*.

This is Phase 3 of Implementation 0: the boundary rules are machine-checkable, not
only documented. A violation here is an architecture change and needs a decision-log
entry before the rule is edited.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .rules import RULES, RULES_BY_NAME, STDLIB_ALWAYS_OK

SRC = Path(__file__).resolve().parents[2] / "src"


def _module_files(module: str) -> list[Path]:
    return sorted((SRC / module).rglob("*.py"))


def _imports(path: Path) -> list[tuple[str, int]]:
    """Every imported top-level name in a file, with its line number.

    Imports inside functions count. A boundary you only cross lazily is still crossed.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import: within the same module, always fine
            if node.module:
                found.append((node.module.split(".")[0], node.lineno))
    return found


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r.name)
def test_module_has_no_banned_imports(rule) -> None:
    banned = dict(rule.banned)
    violations = []
    for path in _module_files(rule.name):
        for name, lineno in _imports(path):
            if name in banned:
                violations.append(
                    f"{path.relative_to(SRC)}:{lineno} imports {name!r} -- {banned[name]}"
                )
    assert not violations, "module boundary violation:\n  " + "\n  ".join(violations)


@pytest.mark.parametrize(
    "rule", [r for r in RULES if r.allowlist is not None], ids=lambda r: r.name
)
def test_module_allowlist(rule) -> None:
    allowed = (
        set(rule.allowlist or ()) | set(rule.extra_allowed) | set(STDLIB_ALWAYS_OK) | {rule.name}
    )
    violations = []
    for path in _module_files(rule.name):
        for name, lineno in _imports(path):
            if name not in allowed:
                violations.append(
                    f"{path.relative_to(SRC)}:{lineno} imports {name!r}, not on {rule.name}'s "
                    f"allowlist -- {rule.notes}"
                )
    assert not violations, "allowlist violation:\n  " + "\n  ".join(violations)


def test_no_pod_module_imports_test_or_simulation_code() -> None:
    violations = []
    for rule in RULES:
        for path in _module_files(rule.name):
            for name, lineno in _imports(path):
                if name in {"simulation", "tests"}:
                    violations.append(
                        f"{path.relative_to(SRC)}:{lineno} imports {name!r}: dev scaffolding "
                        "must never be reachable from flight software"
                    )
    assert not violations, "\n  ".join(violations)


def test_every_prd_module_exists() -> None:
    """[PRD 2.3] names exactly seven modules. All seven must be present."""
    prd_seven = (
        "pod_config",
        "pod_perception",
        "pod_geometry",
        "pod_guidance",
        "pod_state",
        "pod_mavlink",
        "pod_gcs",
    )
    missing = [m for m in prd_seven if not (SRC / m / "__init__.py").exists()]
    assert not missing, f"missing PRD modules: {missing}"
    assert set(prd_seven) <= set(RULES_BY_NAME), "a PRD module has no enforced rule"

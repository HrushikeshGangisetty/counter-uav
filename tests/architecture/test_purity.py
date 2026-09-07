"""pod_geometry, pod_guidance and pod_state are pure [PRD 2.3, 7.2].

"no I/O, no threads, no globals. They are functions of their inputs. This means a
logged flight can be replayed offline for bit-identical guidance output, which turns
tuning questions into unit tests instead of flight tests."

Purity is checked structurally: no `global` statements, no module-level mutable
state, and no calls to the I/O and clock builtins that would make a replay
non-reproducible.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from .rules import PURE_MODULES

SRC = Path(__file__).resolve().parents[2] / "src"

#: Calls that break determinism or purity if made inside a pure module.
FORBIDDEN_CALLS = {
    "open": "file I/O",
    "print": "I/O",
    "input": "I/O",
    "eval": "non-analysable",
    "exec": "non-analysable",
}
#: Attribute calls that read a clock or the environment.
FORBIDDEN_ATTR_CALLS = {
    ("time", "time"): "reads a clock -- pass now_ns in instead",
    ("time", "monotonic"): "reads a clock -- pass now_ns in instead",
    ("time", "time_ns"): "reads a clock -- pass now_ns in instead",
    ("time", "monotonic_ns"): "reads a clock -- pass now_ns in instead",
    ("time", "sleep"): "blocks -- pure modules never sleep",
    ("random", "random"): "non-deterministic",
    ("os", "environ"): "reads global environment",
}


def _files(module: str) -> list[Path]:
    return sorted((SRC / module).rglob("*.py"))


@pytest.mark.parametrize("module", PURE_MODULES)
def test_no_global_statements(module: str) -> None:
    bad = []
    for path in _files(module):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                bad.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert not bad, f"{module} uses global/nonlocal state [PRD 7.2]: {bad}"


@pytest.mark.parametrize("module", PURE_MODULES)
def test_no_module_level_mutable_state(module: str) -> None:
    """Module-level names must be UPPER_CASE constants, classes, functions or type
    aliases. A lower-case module-level binding is state by another name."""
    bad = []
    for path in _files(module):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            targets: list[str] = []
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target.id]
            for name in targets:
                if name.startswith("__") or name.isupper() or name[0].isupper():
                    continue
                bad.append(f"{path.relative_to(SRC)}:{node.lineno} binds {name!r}")
    assert not bad, f"{module} holds module-level mutable state [PRD 7.2]: {bad}"


@pytest.mark.parametrize("module", PURE_MODULES)
def test_no_io_or_clock_calls(module: str) -> None:
    bad = []
    for path in _files(module):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in FORBIDDEN_CALLS:
                bad.append(
                    f"{path.relative_to(SRC)}:{node.lineno} calls {fn.id}() -- {FORBIDDEN_CALLS[fn.id]}"
                )
            elif isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                key = (fn.value.id, fn.attr)
                if key in FORBIDDEN_ATTR_CALLS:
                    bad.append(
                        f"{path.relative_to(SRC)}:{node.lineno} calls {key[0]}.{key[1]}() -- "
                        f"{FORBIDDEN_ATTR_CALLS[key]}"
                    )
    assert not bad, f"{module} is not pure [PRD 2.3, 7.2]:\n  " + "\n  ".join(bad)

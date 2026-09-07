"""Hard invariant 7, enforced [PRD 1.3]:

"Exactly one software module holds the serial handle to the flight controller.
Nothing else may write to it." [PRD 7.2] "If you find yourself wanting a second
writer, the answer is no."

A second writer would begin as a second import. This test refuses the import.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
SERIAL_NAMES = {"pymavlink", "serial", "mavutil"}
SOLE_OWNER = "pod_mavlink"


def test_only_pod_mavlink_may_touch_the_serial_link() -> None:
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        module = path.relative_to(SRC).parts[0]
        if module == SOLE_OWNER:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module.split(".")[0]]
            for n in names:
                if n in SERIAL_NAMES:
                    offenders.append(f"{path.relative_to(SRC)}:{node.lineno} imports {n!r}")
    assert not offenders, (
        "hard invariant 7 violated -- only pod_mavlink may hold the FC serial handle "
        "[PRD 1.3, 7.2]:\n  " + "\n  ".join(offenders)
    )

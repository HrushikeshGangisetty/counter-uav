"""No module-specific ad-hoc copies of the shared contracts.

[PRD 2.3] modules "communicate only through plain dataclasses" --- one definition
each. A second Detection class in pod_perception is how wire schemas drift.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
CONTRACT_NAMES = {
    "FrameMeta",
    "BBox",
    "Detection",
    "TrackedObject",
    "TrackFrame",
    "VehicleState",
    "RCState",
    "LineOfSight",
    "GuidanceInput",
    "VelocityCommand",
    "StateInput",
    "StateOutput",
    "TelemetryFrame",
    "TrackSummary",
    "LatencySample",
    "StageTiming",
    "ModelArtifactMetadata",
}


def test_contracts_are_defined_only_in_pod_contracts() -> None:
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if path.relative_to(SRC).parts[0] == "pod_contracts":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in CONTRACT_NAMES:
                offenders.append(f"{path.relative_to(SRC)}:{node.lineno} redefines {node.name}")
    assert not offenders, (
        "shared contracts must have exactly one definition, in pod_contracts:\n  "
        + "\n  ".join(offenders)
    )

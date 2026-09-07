"""pod_contracts --- the single definition of every cross-module data structure.

WHY THIS PACKAGE EXISTS
-----------------------
[PRD 2.3] names seven modules and says they "communicate only through plain
dataclasses", and [PRD 7.2] requires every cross-module message to carry a capture
timestamp and frame sequence number. It does not say where those dataclasses live.
[DAY1 0] put shared schemas in ``/protocol``. This package is that location, renamed
to the ``pod_*`` convention. It is NOT an eighth architectural module: it holds no
behaviour, owns no resource and imports nothing outside the standard library.

This is an Implementation-0 decision and is recorded as such in
docs/decisions/0015-shared-contracts-package.md.

RULES
-----
* Stdlib only. pod_contracts imports no third-party package and no pod_* module.
* No module-specific copies. If a structure crosses a module boundary it is defined
  here, once. tests/architecture/ enforces this.
* Every dataclass is frozen --- messages are values, not shared mutable state
  [PRD 7.2 single-writer discipline].
"""

from __future__ import annotations

from .detection import BBox, Detection, TrackedObject, TrackFrame
from .enums import (
    CommandDecision,
    DistortionModel,
    FlightMode,
    LatencyStage,
    MissionMode,
    NMSLocation,
    PodState,
    RangeMethod,
)
from .frame import CAPTURE_CLOCK, FrameMeta
from .geometry import LineOfSight
from .guidance import GuidanceInput, VelocityCommand
from .latency import LatencySample, StageTiming
from .model import MODEL_ACCEPTANCE_GATE, ModelArtifactMetadata, QuantisationEvidence
from .registry import CROSS_MODULE_MESSAGES, STAMP_EXEMPT_MESSAGES
from .state import StateInput, StateOutput
from .telemetry import ALLOWED_GCS_COMMANDS, TelemetryFrame, TrackSummary
from .vehicle import HEARTBEAT_GAP_LIMIT_NS, RCState, VehicleState

#: Detection message schema version. Frozen at 1.0 by OD-17 (see
#: docs/decisions/0008-detection-message-schema-v1.md). Bumping this is a decision
#: that requires a decision-log entry.
CONTRACT_VERSION = "1.0"

__all__ = [
    "ALLOWED_GCS_COMMANDS",
    "BBox",
    "CAPTURE_CLOCK",
    "CONTRACT_VERSION",
    "CROSS_MODULE_MESSAGES",
    "CommandDecision",
    "Detection",
    "DistortionModel",
    "FlightMode",
    "FrameMeta",
    "GuidanceInput",
    "HEARTBEAT_GAP_LIMIT_NS",
    "LatencySample",
    "LatencyStage",
    "LineOfSight",
    "MODEL_ACCEPTANCE_GATE",
    "MissionMode",
    "ModelArtifactMetadata",
    "NMSLocation",
    "PodState",
    "QuantisationEvidence",
    "RCState",
    "RangeMethod",
    "STAMP_EXEMPT_MESSAGES",
    "StageTiming",
    "StateInput",
    "StateOutput",
    "TelemetryFrame",
    "TrackFrame",
    "TrackSummary",
    "TrackedObject",
    "VehicleState",
    "VelocityCommand",
]

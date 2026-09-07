"""Pod -> GCS telemetry contract (WebSocket JSON, ~10 Hz) [PRD 2.4, 5.5].

Owner: Person A. Producer: pod_gcs. Consumer: the ground station application.

Serialisation: JSON, field names exactly as spelled here. [PRD 5.5] the Kotlin
kotlinx.serialization mirror is a SECOND definition of this one wire schema --- it
lives at schemas/telemetry.schema.json alongside this file and any change touches
both, or they will diverge.

The command surface in the other direction is deliberately narrow: lock, unlock and
pre-takeoff mode_set only. It must not be able to change break-off radius, velocity
envelopes or mission mode in flight, and must not bypass the governor [PRD 5.5,
1.3 invariants 5 and 6].
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import CommandDecision, MissionMode, PodState

#: The only commands the GCS may send to the pod [PRD 5.5].
ALLOWED_GCS_COMMANDS = ("lock", "unlock", "mode_set")


@dataclass(frozen=True, slots=True)
class TrackSummary:
    track_id: int
    class_name: str
    confidence: float
    bbox_area_fraction: float
    is_locked: bool


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    """CROSS-MODULE MESSAGE. One ~10 Hz telemetry tick to the ground station."""

    capture_ts_ns: int
    frame_seq: int
    state: PodState
    decision: CommandDecision
    mission_mode: MissionMode
    tracks: tuple[TrackSummary, ...]
    locked_track_id: int | None = None
    last_transition_reason: str = ""
    control_latency_p95_ms: float | None = None

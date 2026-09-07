"""Latency instrumentation contract.

Owner: Person A. Producers: every stage. Consumers: the logging harness and pod_gcs.

[PRD 1.5] requires camera-to-actuation latency below 200 ms at p95 "with the full
distribution logged" --- so the contract records per-stage samples, not a summary.
[PRD 6.3] operator glass-to-glass video latency is a SEPARATE figure (target ~300 ms)
and must never be folded into this one.

Units: nanoseconds, CLOCK_MONOTONIC, same clock as FrameMeta.capture_ts_ns.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import LatencyStage
from .frame import FrameMeta


@dataclass(frozen=True, slots=True)
class StageTiming:
    stage: LatencyStage
    enter_ts_ns: int
    exit_ts_ns: int

    def duration_ns(self) -> int:
        return self.exit_ts_ns - self.enter_ts_ns


@dataclass(frozen=True, slots=True)
class LatencySample:
    """CROSS-MODULE MESSAGE. One frame's journey through the pipeline."""

    frame: FrameMeta
    stages: tuple[StageTiming, ...]
    actuation_ts_ns: int | None = None

    def total_ns(self) -> int | None:
        """Camera-to-actuation total, or None if the frame produced no setpoint
        (which is the normal case whenever the governor is SILENT)."""
        if self.actuation_ts_ns is None:
            return None
        return self.actuation_ts_ns - self.frame.capture_ts_ns

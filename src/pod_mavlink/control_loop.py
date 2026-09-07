"""One turn of the control cycle: telemetry in, one governed decision out.

This is the "governor hand-off" half of ``pod_mavlink``'s remit
(``docs/architecture.md``). It wires the pieces that already exist --- it adds no
guidance, no new safety logic, no state of its own beyond "which PodState are we in".

Data flow, one ``tick``::

    rx.snapshot()  ->  VehicleState, RCState
    command_source(now_ns)  ->  PerceptionInputs        (injected; synthetic for now)
        |
        v
    StateInput  ->  pod_state.step()   ->  candidate StateOutput
        |
        v
    pod_state.govern()  ->  governed StateOutput        (FINAL authority [PRD 1.3 #1])
        |
        v
    MavlinkLink.send()  ->  a SET_POSITION_TARGET_LOCAL_NED, or nothing (SILENT)

``PerceptionInputs`` is the seam where a future ``pod_perception`` +
``pod_geometry`` + ``pod_guidance`` chain will feed the machine. It is **not** a
cross-module contract: it is built and consumed inside this module, one call apart,
and never serialised or handed across a boundary --- so it is not in
``pod_contracts.CROSS_MODULE_MESSAGES``. Until that chain exists the caller injects a
source that returns an empty ``PerceptionInputs`` (no frame, no command,
``target_visible=False``), which drives the machine to a SILENT decision every tick.
That is the point of this pass: exercise the architecture, not fly.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from pod_config import SafetyEnvelope
from pod_contracts import (
    CommandDecision,
    FrameMeta,
    MissionMode,
    PodState,
    StateInput,
    StateOutput,
    VelocityCommand,
)
from pod_state import govern, step

from .link import MavlinkLink
from .rx_runtime import MavlinkRxRuntime

_log = logging.getLogger("pod_mavlink.control_loop")


@dataclass(frozen=True, slots=True)
class PerceptionInputs:
    """The per-tick inputs the control loop does *not* own itself.

    Everything here would, in a full build, come from the perception/geometry/
    guidance chain. Defaults are the "nothing to pursue" case: the loop still ticks,
    and goes SILENT.
    """

    frame: FrameMeta | None = None
    proposed_command: VelocityCommand | None = None
    target_visible: bool = False
    bbox_area_fraction: float = 0.0
    locked_track_id: int | None = None


#: A per-tick input source: given the loop's ``now_ns``, return this tick's inputs.
CommandSource = Callable[[int], PerceptionInputs]


def null_command_source(_now_ns: int) -> PerceptionInputs:
    """The default source: never proposes anything. Every tick governs to SILENT."""
    return PerceptionInputs()


@dataclass(frozen=True, slots=True)
class CycleReport:
    """What one ``tick`` did. Returned to the caller and written to the log."""

    tick_index: int
    now_ns: int
    state: PodState
    previous_state: PodState | None
    decision: CommandDecision
    reason: str
    transmitted: bool
    heartbeat_ok: bool
    duration_ns: int

    def as_log_fields(self) -> dict[str, object]:
        return {
            "tick": self.tick_index,
            "state": self.state.value,
            "prev": self.previous_state.value if self.previous_state else None,
            "decision": self.decision.value,
            "reason": self.reason,
            "sent": self.transmitted,
            "hb_ok": self.heartbeat_ok,
            "tick_ms": round(self.duration_ns / 1_000_000, 3),
        }


@dataclass
class ControlLoop:
    """Holds the wiring and the single mutable field of interest: ``state``.

    ``envelope`` and ``mission_mode`` are passed in already resolved (decision 0019 /
    0020 pattern) --- this module never reads ``pod_config`` itself, so a still-OPEN
    value surfaces as ``ConfigOpenError`` from ``step()``/``govern()`` at the point of
    use, not as a guess here. ``target_system`` / ``target_component`` have no default
    for the same reason they have none on ``MavlinkLink.send()`` (decision 0021): no
    document assigns MAVLink addressing.
    """

    link: MavlinkLink
    rx: MavlinkRxRuntime
    envelope: SafetyEnvelope
    mission_mode: MissionMode
    target_system: int
    target_component: int
    command_source: CommandSource = null_command_source
    state: PodState = PodState.IDLE
    now_ns: Callable[[], int] = time.monotonic_ns
    _boot_ns: int = field(init=False)
    _tick_index: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._boot_ns = self.now_ns()

    def tick(self, now_ns: int) -> CycleReport:
        """Run one control cycle. ``now_ns`` is this tick's reference clock reading
        (supplied by the scheduler), used for staleness/heartbeat arithmetic and as
        ``StateInput.now_ns`` --- never read from a clock inside the pure logic."""
        t0 = self.now_ns()
        vehicle, rc = self.rx.snapshot()
        pi = self.command_source(now_ns)

        si = StateInput(
            now_ns=now_ns,
            frame=pi.frame,
            vehicle=vehicle,
            rc=rc,
            mission_mode=self.mission_mode,
            proposed_command=pi.proposed_command,
            locked_track_id=pi.locked_track_id,
            target_visible=pi.target_visible,
            bbox_area_fraction=pi.bbox_area_fraction,
        )

        candidate = step(self.state, si, self.envelope)
        governed = govern(candidate, si, self.envelope)
        self.state = governed.state

        transmitted = self._transmit(governed, now_ns)

        report = CycleReport(
            tick_index=self._tick_index,
            now_ns=now_ns,
            state=governed.state,
            previous_state=governed.previous_state,
            decision=governed.decision,
            reason=governed.reason,
            transmitted=transmitted,
            heartbeat_ok=vehicle.heartbeat_ok(now_ns),
            duration_ns=self.now_ns() - t0,
        )
        self._tick_index += 1
        _log.info("control_cycle %s", report.as_log_fields())
        return report

    def _transmit(self, governed: StateOutput, now_ns: int) -> bool:
        """Hand the governed output to the link. ``send()`` itself is the last gate:
        it transmits only for ``decision is SEND`` with a non-None command, and never
        a zero-velocity substitute [PRD 4.3]."""
        time_boot_ms = max(0, (now_ns - self._boot_ns) // 1_000_000)
        return self.link.send(
            governed,
            time_boot_ms=int(time_boot_ms),
            target_system=self.target_system,
            target_component=self.target_component,
        )

"""pod_state input/output contract --- state machine plus safety governor.

Owner: Person A. Producer: pod_state (pure). Consumer: pod_mavlink.

The output deliberately separates "which state are we in" from "may anything be
sent". [PRD 4.3]: on any precondition failure the governor stops sending setpoints
rather than sending zero velocity. A StateOutput with decision=SILENT carries
command=None --- there is no zero-velocity fallback anywhere in this contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import CommandDecision, MissionMode, PodState
from .frame import FrameMeta
from .guidance import VelocityCommand
from .vehicle import RCState, VehicleState


@dataclass(frozen=True, slots=True)
class StateInput:
    """CROSS-MODULE MESSAGE. Everything the state machine may look at.

    now_ns is passed in rather than read from a clock: pod_state is pure, so a logged
    flight replays to bit-identical output [PRD 2.3].
    """

    now_ns: int
    frame: FrameMeta | None
    vehicle: VehicleState
    rc: RCState
    mission_mode: MissionMode
    proposed_command: VelocityCommand | None
    locked_track_id: int | None = None
    target_visible: bool = False
    bbox_area_fraction: float = 0.0


@dataclass(frozen=True, slots=True)
class StateOutput:
    """CROSS-MODULE MESSAGE.

    Attributes:
        decision: SEND or SILENT. SILENT means pod_mavlink transmits nothing this
            tick and lets the FC's own GUIDED setpoint timeout (~3 s [PRD 5.4]) take
            over.
        command: None whenever decision is SILENT. Never a zero-velocity stand-in.
        reason: Short machine-readable reason for the decision/transition, logged and
            forwarded to the GCS.
    """

    state: PodState
    decision: CommandDecision
    command: VelocityCommand | None
    reason: str
    previous_state: PodState | None = None

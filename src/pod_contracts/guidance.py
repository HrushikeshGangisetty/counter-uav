"""pod_guidance input/output contract.

Owner: Person A. Producer: pod_guidance (pure). Consumer: pod_state.

[PRD 6.1] proportional navigation must be implementable behind the SAME interface as
the pursuit law, so switching is a configuration change rather than a rewrite. That
is why the law is selected by name in GuidanceInput and why the output type carries
no law-specific fields.

Units: velocities m/s in the BODY frame (x forward, y right, z down); yaw_rate rad/s
positive to the right. These map 1:1 onto SET_POSITION_TARGET_LOCAL_NED in
MAV_FRAME_BODY_NED with only vx, vy, vz and yaw_rate unmasked [PRD 5.4].
"""

from __future__ import annotations

from dataclasses import dataclass

from .frame import FrameMeta
from .geometry import LineOfSight
from .vehicle import VehicleState


@dataclass(frozen=True, slots=True)
class GuidanceInput:
    """CROSS-MODULE MESSAGE."""

    frame: FrameMeta
    los: LineOfSight
    vehicle: VehicleState
    law: str = "pursuit"


@dataclass(frozen=True, slots=True)
class VelocityCommand:
    """CROSS-MODULE MESSAGE. A desired body-frame velocity. Advisory only: emitting
    one does not mean it will be sent --- pod_state and the governor decide that
    [PRD 1.3 invariant 1]."""

    frame: FrameMeta
    vx_ms: float
    vy_ms: float
    vz_ms: float
    yaw_rate_rads: float

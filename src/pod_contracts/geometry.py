"""pod_geometry output contract.

Owner of the module internals: Person C (Sreenija). Owner of this interface:
Person A. Producer: pod_geometry (pure). Consumer: pod_guidance.

Units: los_body_* is a dimensionless unit vector in the vehicle BODY frame
(x forward, y right, z down), consistent with MAV_FRAME_BODY_NED [PRD 5.4].
range_m in metres. range_rate_ms in m/s, positive = opening.

OD-06 is OPEN: monocular vision cannot observe range [PRD 6.1]. range_m and
range_rate_ms are therefore Optional and are None until a method is chosen and
implemented. Consumers must handle None; they must not substitute a default.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import RangeMethod
from .frame import FrameMeta


@dataclass(frozen=True, slots=True)
class LineOfSight:
    """CROSS-MODULE MESSAGE. Body-frame line of sight to one tracked target."""

    frame: FrameMeta
    track_id: int
    los_body_x: float
    los_body_y: float
    los_body_z: float
    bbox_area_fraction: float
    range_method: RangeMethod = RangeMethod.NONE
    range_m: float | None = None
    range_rate_ms: float | None = None
    valid: bool = True

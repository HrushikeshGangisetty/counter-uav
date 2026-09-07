"""Configuration schema. Frozen dataclasses; no I/O in this file.

Units are stated on every field. Where a value is not settled in any project
document it is the OPEN sentinel --- never a plausible-looking placeholder number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pod_contracts import DistortionModel, MissionMode


class _Open:
    """Sentinel for a value whose decision is still OPEN."""

    _instance: _Open | None = None

    def __new__(cls) -> _Open:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "OPEN"

    def __bool__(self) -> bool:
        return False


#: Sentinel meaning "this decision is not made". YAML spells it ``OPEN``.
OPEN = _Open()


def is_open(value: Any) -> bool:
    return value is OPEN


@dataclass(frozen=True, slots=True)
class CameraIntrinsics:
    """Output of Person C's OpenCV calibration [PRD 4.1, 5.4].

    ⚠ OD-02 is OPEN and gates M2: "Until fx, fy, cx, cy and the distortion
    coefficients are measured on the actual camera and lens, every number downstream
    of the geometry stage is fabricated. Do this before M2, not before M4."
    Shipped values are OPEN; the shape of the file is fixed now so Person C has a
    destination.

    ⚠ OD-20 is OPEN: distortion_model is configuration, never a hard-coded call. The
    interim 160 deg fisheye needs FISHEYE_EQUIDISTANT (k1-k4); a telephoto flight
    lens (OD-19) flips back to PINHOLE_RADTAN (k1,k2,p1,p2,k3).

    Units: fx, fy, cx, cy in pixels. distortion_coeffs dimensionless, OpenCV order.
    """

    camera_id: int
    width_px: int
    height_px: int
    distortion_model: DistortionModel | _Open
    fx_px: float | _Open
    fy_px: float | _Open
    cx_px: float | _Open
    cy_px: float | _Open
    distortion_coeffs: tuple[float, ...] | _Open
    calibrated: bool = False
    calibration_id: str = ""
    reprojection_error_px: float | _Open = OPEN
    lens_description: str = ""

    def require_calibrated(self) -> None:
        from .errors import ConfigOpenError

        if not self.calibrated or any(
            is_open(v) for v in (self.fx_px, self.fy_px, self.cx_px, self.cy_px)
        ):
            raise ConfigOpenError(
                f"camera {self.camera_id} intrinsics are OPEN (OD-02). "
                "pod_geometry output would be fabricated; refusing."
            )


@dataclass(frozen=True, slots=True)
class RCChannelMap:
    """RC channel numbers for the pod's switches [DAY1 0], [PRD 1.3 invariant 4].

    ⚠ OPEN: no project document assigns specific channel numbers. The three switches
    themselves are documented; their channel indices are not, so they ship as OPEN.
    """

    ai_enable_channel: int | _Open = OPEN
    lock_trigger_channel: int | _Open = OPEN
    kill_switch_channel: int | _Open = OPEN
    mission_mode_channel: int | _Open = OPEN
    high_threshold_us: int | _Open = OPEN


@dataclass(frozen=True, slots=True)
class SafetyEnvelope:
    """Boot-time immutable safety parameters [PRD 7.2].

    Not runtime-controllable from the ground station [PRD 1.3 invariant 6].

    Values from [ARCH Performance Envelope] (not superseded) are populated;
    per-airframe values that must be sized against MEASURED M3 latency (OD-12) are
    OPEN. [PRD 4.8] "The break-off radius must be sized against measured end-to-end
    latency translated into distance, not against the millisecond figure."
    """

    max_pursuit_speed_ms: float | _Open = OPEN
    max_cruise_speed_ms: float | _Open = OPEN
    max_altitude_m: float | _Open = OPEN
    breakoff_radius_m: float | _Open = OPEN
    bbox_area_terminal: float | _Open = OPEN
    bbox_area_breakoff: float | _Open = OPEN
    target_lost_timeout_s: float | _Open = OPEN
    lost_state_timeout_s: float | _Open = OPEN
    max_frame_age_ms: float | _Open = OPEN
    heartbeat_gap_limit_ms: float | _Open = OPEN


@dataclass(frozen=True, slots=True)
class AirframeConfig:
    """Per-airframe values. [PRD 1.1] per-airframe differences are confined to a thin
    mechanical adapter plate and a configuration file --- this is that file."""

    airframe_id: str
    description: str = ""
    safety: SafetyEnvelope = field(default_factory=SafetyEnvelope)


@dataclass(frozen=True, slots=True)
class MissionConfig:
    """Mission mode as latched at takeoff [PRD 1.3 invariant 5]."""

    mode: MissionMode | _Open = OPEN
    latched_at_takeoff: bool = True


@dataclass(frozen=True, slots=True)
class PodConfig:
    """The whole boot-time configuration tree."""

    airframe: AirframeConfig
    mission: MissionConfig
    rc: RCChannelMap
    cameras: tuple[CameraIntrinsics, ...] = ()
    source_paths: tuple[str, ...] = ()

    def camera(self, camera_id: int) -> CameraIntrinsics:
        for c in self.cameras:
            if c.camera_id == camera_id:
                return c
        from .errors import ConfigError

        raise ConfigError(f"no intrinsics configured for camera {camera_id}")

    def open_fields(self) -> tuple[str, ...]:
        """Every still-OPEN value, as dotted paths. Logged at boot so an operator can
        see exactly which decisions the running system does not have."""
        found: list[str] = []

        def walk(prefix: str, obj: Any) -> None:
            if not hasattr(obj, "__dataclass_fields__"):
                return
            for name in obj.__dataclass_fields__:
                value = getattr(obj, name)
                path = f"{prefix}.{name}" if prefix else name
                if is_open(value):
                    found.append(path)
                elif hasattr(value, "__dataclass_fields__"):
                    walk(path, value)
                elif isinstance(value, tuple):
                    for i, item in enumerate(value):
                        walk(f"{path}[{i}]", item)

        walk("", self)
        return tuple(found)

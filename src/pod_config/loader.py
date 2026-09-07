"""YAML loading and boot-time-immutability enforcement.

The only file in pod_config that touches the filesystem.
"""

from __future__ import annotations

import os
from typing import Any

import yaml

from pod_contracts import DistortionModel, MissionMode

from .errors import ConfigError, ConfigReloadError
from .schema import (
    OPEN,
    AirframeConfig,
    CameraIntrinsics,
    MissionConfig,
    PodConfig,
    RCChannelMap,
    SafetyEnvelope,
)

_LOADED: PodConfig | None = None

_OPEN_TOKENS = {"open", "tbd", "unspecified", None}


def _v(raw: Any) -> Any:
    """Map a YAML scalar to a value or the OPEN sentinel."""
    if isinstance(raw, str) and raw.strip().lower() in _OPEN_TOKENS:
        return OPEN
    if raw is None:
        return OPEN
    return raw


def _read(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        raise ConfigError(f"config file not found: {path}")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"config file {path} must contain a mapping at the top level")
    return data


def _safety(d: dict[str, Any]) -> SafetyEnvelope:
    return SafetyEnvelope(
        max_pursuit_speed_ms=_v(d.get("max_pursuit_speed_ms")),
        max_cruise_speed_ms=_v(d.get("max_cruise_speed_ms")),
        max_altitude_m=_v(d.get("max_altitude_m")),
        breakoff_radius_m=_v(d.get("breakoff_radius_m")),
        bbox_area_terminal=_v(d.get("bbox_area_terminal")),
        bbox_area_breakoff=_v(d.get("bbox_area_breakoff")),
        target_lost_timeout_s=_v(d.get("target_lost_timeout_s")),
        lost_state_timeout_s=_v(d.get("lost_state_timeout_s")),
        max_frame_age_ms=_v(d.get("max_frame_age_ms")),
        heartbeat_gap_limit_ms=_v(d.get("heartbeat_gap_limit_ms")),
        control_watchdog_timeout_ms=_v(d.get("control_watchdog_timeout_ms")),
    )


def _intrinsics(d: dict[str, Any]) -> CameraIntrinsics:
    model = _v(d.get("distortion_model"))
    if model is not OPEN:
        model = DistortionModel(model)
    coeffs = _v(d.get("distortion_coeffs"))
    if coeffs is not OPEN:
        coeffs = tuple(float(c) for c in coeffs)
    return CameraIntrinsics(
        camera_id=int(d["camera_id"]),
        width_px=int(d.get("width_px", 0)),
        height_px=int(d.get("height_px", 0)),
        distortion_model=model,
        fx_px=_v(d.get("fx_px")),
        fy_px=_v(d.get("fy_px")),
        cx_px=_v(d.get("cx_px")),
        cy_px=_v(d.get("cy_px")),
        distortion_coeffs=coeffs,
        calibrated=bool(d.get("calibrated", False)),
        calibration_id=str(d.get("calibration_id", "")),
        reprojection_error_px=_v(d.get("reprojection_error_px")),
        lens_description=str(d.get("lens_description", "")),
    )


def load_pod_config(
    pod_yaml: str,
    airframe_yaml: str,
    camera_yamls: tuple[str, ...] = (),
    *,
    reload_for_tests: bool = False,
) -> PodConfig:
    """Load the boot-time configuration. Call once, at startup.

    Raises ConfigReloadError on a second call in the same process, because
    safety-critical configuration is boot-time immutable [PRD 7.2]. Tests pass
    reload_for_tests=True.
    """
    global _LOADED
    if _LOADED is not None and not reload_for_tests:
        raise ConfigReloadError(
            "pod configuration is boot-time immutable [PRD 7.2]; it has already been "
            "loaded in this process"
        )

    pod = _read(pod_yaml)
    airframe_raw = _read(airframe_yaml)

    mission_raw = _v(pod.get("mission", {}).get("mode"))
    mission = MissionConfig(
        mode=mission_raw if mission_raw is OPEN else MissionMode(mission_raw),
        latched_at_takeoff=True,
    )

    rc_raw = pod.get("rc_channels", {}) or {}
    rc = RCChannelMap(
        ai_enable_channel=_v(rc_raw.get("ai_enable_channel")),
        lock_trigger_channel=_v(rc_raw.get("lock_trigger_channel")),
        kill_switch_channel=_v(rc_raw.get("kill_switch_channel")),
        mission_mode_channel=_v(rc_raw.get("mission_mode_channel")),
        high_threshold_us=_v(rc_raw.get("high_threshold_us")),
    )

    airframe = AirframeConfig(
        airframe_id=str(airframe_raw.get("airframe_id", "UNSPECIFIED")),
        description=str(airframe_raw.get("description", "")),
        safety=_safety(airframe_raw.get("safety", {}) or {}),
    )

    cameras = tuple(_intrinsics(_read(p)) for p in camera_yamls)

    cfg = PodConfig(
        airframe=airframe,
        mission=mission,
        rc=rc,
        cameras=cameras,
        source_paths=(pod_yaml, airframe_yaml, *camera_yamls),
    )
    _LOADED = cfg
    return cfg


def get_pod_config() -> PodConfig:
    if _LOADED is None:
        raise ConfigError("pod configuration has not been loaded")
    return _LOADED


def reset_for_tests() -> None:
    """Clear the boot-time latch. Test-only."""
    global _LOADED
    _LOADED = None

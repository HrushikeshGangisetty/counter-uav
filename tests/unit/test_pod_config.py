"""pod_config: OPEN values stay OPEN, and safety config is boot-time immutable."""

from __future__ import annotations

import dataclasses

import pytest

from pod_config import (
    ConfigOpenError,
    ConfigReloadError,
    is_open,
    load_pod_config,
)


def _load(configs_dir, **kw):
    return load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (
            str(configs_dir / "camera" / "intrinsics_cam0.yaml"),
            str(configs_dir / "camera" / "intrinsics_cam1.yaml"),
        ),
        **kw,
    )


def test_shipped_config_loads(configs_dir) -> None:
    cfg = _load(configs_dir)
    assert cfg.airframe.airframe_id == "TEMPLATE"
    assert len(cfg.cameras) == 2


def test_open_values_are_the_sentinel_not_a_number(configs_dir) -> None:
    """The values that no document settles must not have quietly acquired one."""
    cfg = _load(configs_dir)
    assert is_open(cfg.airframe.safety.breakoff_radius_m), "OD-12 is OPEN"
    assert is_open(cfg.airframe.safety.bbox_area_terminal)
    assert is_open(cfg.rc.ai_enable_channel), "RC channel numbers are in no document"
    assert is_open(cfg.mission.mode), "mission mode is selected per sortie"


def test_documented_values_are_present(configs_dir) -> None:
    """Values [ARCH Performance Envelope] does state are populated, not OPEN."""
    safety = _load(configs_dir).airframe.safety
    assert safety.max_pursuit_speed_ms == 40.0
    assert safety.max_altitude_m == 100.0
    assert safety.target_lost_timeout_s == 1.5
    assert safety.lost_state_timeout_s == 5.0
    assert safety.heartbeat_gap_limit_ms == 500


def test_uncalibrated_intrinsics_refuse_to_be_used(configs_dir) -> None:
    """OD-02: geometry against uncalibrated intrinsics fabricates every downstream
    number [PRD 4.3]. It must fail loudly, not default."""
    cam0 = _load(configs_dir).camera(0)
    with pytest.raises(ConfigOpenError):
        cam0.require_calibrated()


def test_config_is_boot_time_immutable(configs_dir) -> None:
    """[PRD 7.2] safety-critical configuration loads at startup and cannot change."""
    _load(configs_dir)
    with pytest.raises(ConfigReloadError):
        _load(configs_dir)


def test_config_objects_cannot_be_mutated(configs_dir) -> None:
    cfg = _load(configs_dir)
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.airframe.safety.breakoff_radius_m = 25.0  # type: ignore[misc]


def test_open_fields_are_reportable(configs_dir) -> None:
    """Boot logs must be able to state exactly which decisions are missing."""
    open_fields = _load(configs_dir).open_fields()
    assert "airframe.safety.breakoff_radius_m" in open_fields
    assert any(f.startswith("cameras[0]") for f in open_fields)

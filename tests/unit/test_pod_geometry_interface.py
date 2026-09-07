"""pod_geometry: the interface exists and refuses to fabricate numbers.

OD-02 is OPEN and gates M2 [PRD 5.4]. Until intrinsics are measured, geometry must
raise, not return.
"""

from __future__ import annotations

import inspect

import pytest

from pod_geometry import los_from_track, undistort_point


def test_los_signature_is_stable() -> None:
    """Person C implements the body; Person A owns this signature."""
    params = list(inspect.signature(los_from_track).parameters)
    assert params == ["track", "frame", "intrinsics", "vehicle"]


def test_geometry_refuses_uncalibrated_intrinsics(configs_dir) -> None:
    from pod_config import load_pod_config

    cfg = load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (str(configs_dir / "camera" / "intrinsics_cam0.yaml"),),
    )
    from pod_config import ConfigOpenError

    with pytest.raises(ConfigOpenError):
        undistort_point(10.0, 10.0, cfg.camera(0))

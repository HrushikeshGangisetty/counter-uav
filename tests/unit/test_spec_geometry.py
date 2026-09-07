"""Executable specification for pod_geometry. xfail(strict) until OD-02 closes."""

from __future__ import annotations

import pytest

from pod_geometry import los_from_track
from simulation.mocks import make_frame, make_track_frame, make_vehicle_state

M2 = pytest.mark.xfail(strict=True, reason="pod_geometry is M2 / Person C, blocked on OD-02")


@M2
def test_los_passes_the_stamp_through(configs_dir) -> None:
    """[PRD 2.3] downstream consumers must still be able to reject stale data."""
    from pod_config import load_pod_config

    cfg = load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (str(configs_dir / "camera" / "intrinsics_cam0.yaml"),),
    )
    tf = make_track_frame(seq=5)
    los = los_from_track(tf.tracks[0], tf.frame, cfg.camera(0), make_vehicle_state())
    assert los.frame.frame_seq == 5
    assert los.frame.capture_ts_ns == tf.frame.capture_ts_ns


@M2
def test_range_is_none_until_od06_closes(configs_dir) -> None:
    """[PRD 6.1] monocular vision cannot observe range. No silent proxy."""
    from pod_config import load_pod_config

    cfg = load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (str(configs_dir / "camera" / "intrinsics_cam0.yaml"),),
    )
    tf = make_track_frame()
    los = los_from_track(tf.tracks[0], make_frame(), cfg.camera(0), make_vehicle_state())
    assert los.range_m is None

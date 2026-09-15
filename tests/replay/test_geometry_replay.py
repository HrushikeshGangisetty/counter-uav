"""Synthetic-camera-to-geometry replay path.

Proves the semantic chain the team can build against before real camera hardware
arrives:

    synthetic frame -> synthetic detection/bbox -> image coordinates
        -> camera-frame ray

using only synthetic scenarios (``simulation.synthetic``) and a synthetic, TEST-ONLY
calibrated ``CameraIntrinsics`` (the ``synthetic_calibrated_intrinsics`` fixture in
``tests/conftest.py``). Nothing here is a measurement: OD-02 (intrinsics) and OD-20
(distortion model) stay OPEN, and this file must never be a source of default
production configuration.

Every function exercised here is pure (``pod_geometry``, ``simulation.synthetic``):
no clock, no I/O, no globals [PRD 2.3]. See ``docs/synthetic_replay.md`` for the
narrative version of this path and what it intentionally does not model.
"""

from __future__ import annotations

import pytest

from pod_contracts import BBox, FrameMeta, TrackedObject, TrackFrame
from pod_geometry import bbox_center_to_normalized, camera_ray_from_normalized
from simulation.synthetic import (
    closing_target,
    generate,
    target_appears,
    target_centered,
    target_crossing,
    target_high,
    target_left,
    target_low,
    target_right,
)
from tools.ml.mock import single_target_detector


def _only_bbox(tf):
    assert len(tf.tracks) == 1
    return tf.tracks[0].detection.bbox


# --- frame -> detection -> bbox centre -> normalised coordinate ----------------


def test_centred_target_normalises_to_the_origin() -> None:
    tf = next(iter(generate(target_centered())))
    point = bbox_center_to_normalized(_only_bbox(tf), tf.frame)
    assert point.nx == pytest.approx(0.0, abs=1e-9)
    assert point.ny == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize(
    "scenario_fn,expect_nx,expect_ny",
    [
        (target_left, "neg", "zero"),
        (target_right, "pos", "zero"),
        (target_high, "zero", "neg"),
        (target_low, "zero", "pos"),
    ],
)
def test_static_positions_normalise_to_the_expected_sign(scenario_fn, expect_nx, expect_ny) -> None:
    tf = next(iter(generate(scenario_fn())))
    point = bbox_center_to_normalized(_only_bbox(tf), tf.frame)
    checks = {
        "neg": lambda v: v < 0,
        "pos": lambda v: v > 0,
        "zero": lambda v: v == pytest.approx(0.0),
    }
    assert checks[expect_nx](point.nx)
    assert checks[expect_ny](point.ny)


def test_frame_identity_is_preserved_through_the_chain() -> None:
    """Normalising a bbox centre must not disturb the frame stamp it came from
    [PRD 2.3, 7.2] --- the chain reads frame metadata, it does not consume it."""
    tf = next(iter(generate(target_left(frames=1))))
    before = tf.frame
    bbox_center_to_normalized(_only_bbox(tf), tf.frame)
    assert tf.frame is before
    assert tf.frame.frame_seq == before.frame_seq
    assert tf.frame.capture_ts_ns == before.capture_ts_ns
    assert tf.frame.width_px == before.width_px
    assert tf.frame.height_px == before.height_px


def test_moving_target_stamps_are_correct_per_frame_and_deterministic() -> None:
    """Walking a sequence must not cross-wire one frame's stamp with another
    frame's detection, and the whole sequence must reproduce exactly."""
    run_a = list(generate(target_crossing(frames=30)))
    run_b = list(generate(target_crossing(frames=30)))
    assert run_a == run_b, "synthetic replay must be deterministic"

    xs = []
    for i, tf in enumerate(run_a):
        assert tf.frame.frame_seq == i
        point = bbox_center_to_normalized(_only_bbox(tf), tf.frame)
        xs.append(point.nx)
    assert xs == sorted(xs), "target_crossing moves strictly left to right"
    assert xs[0] < 0 < xs[-1]


# --- normalised coordinate -> camera-frame ray ----------------------------------


def test_centred_target_ray_is_the_optical_axis(synthetic_calibrated_intrinsics) -> None:
    intr = synthetic_calibrated_intrinsics()
    tf = next(iter(generate(target_centered())))
    point = bbox_center_to_normalized(_only_bbox(tf), tf.frame)
    ray = camera_ray_from_normalized(point, intr)
    assert ray == pytest.approx((0.0, 0.0, 1.0))


@pytest.mark.parametrize(
    "scenario_fn,expect_x,expect_y",
    [
        (target_left, "neg", "zero"),
        (target_right, "pos", "zero"),
        (target_high, "zero", "neg"),
        (target_low, "zero", "pos"),
    ],
)
def test_static_positions_ray_has_expected_sign_and_unit_length(
    synthetic_calibrated_intrinsics, scenario_fn, expect_x, expect_y
) -> None:
    intr = synthetic_calibrated_intrinsics()
    tf = next(iter(generate(scenario_fn())))
    point = bbox_center_to_normalized(_only_bbox(tf), tf.frame)
    x, y, z = camera_ray_from_normalized(point, intr)

    checks = {
        "neg": lambda v: v < 0,
        "pos": lambda v: v > 0,
        "zero": lambda v: v == pytest.approx(0.0),
    }
    assert checks[expect_x](x)
    assert checks[expect_y](y)
    assert z > 0
    assert (x * x + y * y + z * z) == pytest.approx(1.0)


def test_full_chain_ray_is_deterministic(synthetic_calibrated_intrinsics) -> None:
    intr = synthetic_calibrated_intrinsics()

    def _ray():
        tf = next(iter(generate(target_right(frames=1))))
        point = bbox_center_to_normalized(_only_bbox(tf), tf.frame)
        return camera_ray_from_normalized(point, intr)

    assert _ray() == _ray()


# --- absent-target and invalid-input handling -----------------------------------


def test_no_target_frame_has_nothing_to_project() -> None:
    """A dropout frame is a valid frame with an empty track list, not a missing
    record --- there is no bbox to run through the chain, and callers must check
    for that themselves rather than the geometry layer inventing a detection."""
    frames = list(generate(target_appears(frames=10, appears_at=5)))
    absent, present = frames[:5], frames[5:]
    assert all(tf.tracks == () for tf in absent)
    assert all(tf.by_id(1) is None for tf in absent)
    assert all(len(tf.tracks) == 1 for tf in present)


def test_invalid_frame_metadata_is_rejected_before_geometry_runs() -> None:
    """A frame with a non-positive size cannot be normalised --- the pure function
    refuses rather than dividing by zero or silently producing a point."""
    bad_frame = FrameMeta(camera_id=0, frame_seq=0, capture_ts_ns=0, width_px=0, height_px=1088)
    bbox = BBox(x_px=10.0, y_px=10.0, w_px=5.0, h_px=5.0)
    with pytest.raises(ValueError, match="dimensions must be positive"):
        bbox_center_to_normalized(bbox, bad_frame)


# --- bridging to Person B's MockDetector seam (tools.ml.mock.detector) ---------


def test_synthetic_frame_drives_mock_detector_into_the_geometry_chain(
    synthetic_calibrated_intrinsics,
) -> None:
    """The conceptual path this pass targets: SyntheticFrame -> MockDetector ->
    Detection[] -> image coordinates -> camera ray.

    ``simulation.synthetic.generate`` normally hands out a ``TrackFrame`` directly,
    standing in for a detector. This proves the same synthetic ``FrameMeta`` also
    drives Person B's actual ``Detector`` seam (``tools.ml.mock.detector``) once its
    output is composed into a ``TrackFrame`` by the caller (exactly as
    ``tools/ml/mock/detector.py``'s own docstring specifies is the caller's job), and
    that the result still flows through the same geometry chain with the stamp
    intact.
    """
    intr = synthetic_calibrated_intrinsics()
    synthetic_tf = next(iter(generate(target_right(frames=1))))
    frame = synthetic_tf.frame
    detection = synthetic_tf.tracks[0].detection

    detector = single_target_detector(detection, visible_frames=frozenset({frame.frame_seq}))
    detections = detector.detect(frame)
    assert detections == (detection,)

    track_frame = TrackFrame(
        frame=frame,
        tracks=tuple(TrackedObject(track_id=i, detection=d) for i, d in enumerate(detections)),
    )
    assert track_frame.frame is frame

    point = bbox_center_to_normalized(_only_bbox(track_frame), track_frame.frame)
    ray = camera_ray_from_normalized(point, intr)
    assert ray[0] > 0  # target_right
    assert sum(c * c for c in ray) == pytest.approx(1.0)


def test_stale_frame_is_detectable_via_age_ns_regardless_of_arrival_order() -> None:
    """[PRD 2.3, 7.2] 'Consumers reject stale data themselves.' A consumer needs
    nothing but ``age_ns`` against its own clock reading to tell an old frame from
    a fresh one, independent of the order frames are handed to it."""
    frames = list(generate(closing_target(frames=5)))
    newest = frames[-1].frame
    oldest = frames[0].frame
    now_ns = newest.capture_ts_ns + 1_000_000
    assert oldest.age_ns(now_ns) > newest.age_ns(now_ns) > 0

"""tools.ml.mock.detector: the deterministic Detector seam."""

from __future__ import annotations

from pod_contracts import BBox, Detection, FrameMeta, TrackedObject, TrackFrame
from tools.ml.mock.detector import MockDetector, constant_detector, single_target_detector


def _frame(seq: int) -> FrameMeta:
    return FrameMeta(
        camera_id=0, frame_seq=seq, capture_ts_ns=seq * 1000, width_px=100, height_px=100
    )


def _detection(class_name: str = "uav") -> Detection:
    return Detection(
        class_id=0, class_name=class_name, confidence=0.9, bbox=BBox(1.0, 1.0, 5.0, 5.0)
    )


# --- MockDetector basics -----------------------------------------------------------


def test_default_detector_returns_nothing() -> None:
    detector = MockDetector()
    assert detector.detect(_frame(0)) == ()
    assert detector.detect(_frame(999)) == ()


def test_schedule_controls_detections_per_frame_seq() -> None:
    d0 = _detection("uav")
    detector = MockDetector(schedule={3: (d0,)})
    assert detector.detect(_frame(3)) == (d0,)
    assert detector.detect(_frame(4)) == ()


def test_detect_is_deterministic() -> None:
    detector = MockDetector(schedule={1: (_detection(),)})
    assert detector.detect(_frame(1)) == detector.detect(_frame(1))


def test_detect_does_not_depend_on_frame_fields_other_than_seq() -> None:
    d0 = _detection()
    detector = MockDetector(schedule={7: (d0,)})
    a = FrameMeta(camera_id=0, frame_seq=7, capture_ts_ns=111, width_px=100, height_px=100)
    b = FrameMeta(camera_id=1, frame_seq=7, capture_ts_ns=222, width_px=640, height_px=480)
    assert detector.detect(a) == detector.detect(b) == (d0,)


# --- multiple targets / no target ---------------------------------------------------


def test_multiple_targets_in_one_frame() -> None:
    d0, d1 = _detection("uav"), _detection("uav")
    detector = MockDetector(schedule={0: (d0, d1)})
    result = detector.detect(_frame(0))
    assert result == (d0, d1)
    assert len(result) == 2


def test_no_target_case_is_empty_tuple() -> None:
    detector = MockDetector(schedule={0: ()})
    assert detector.detect(_frame(0)) == ()


# --- constant_detector / single_target_detector ------------------------------------


def test_constant_detector_returns_same_detections_every_frame() -> None:
    d0 = _detection()
    detector = constant_detector((d0,))
    assert detector.detect(_frame(0)) == (d0,)
    assert detector.detect(_frame(100)) == (d0,)


def test_single_target_detector_visible_everywhere_by_default() -> None:
    d0 = _detection()
    detector = single_target_detector(d0)
    assert detector.detect(_frame(0)) == (d0,)
    assert detector.detect(_frame(50)) == (d0,)


def test_single_target_detector_dropout_window() -> None:
    d0 = _detection()
    detector = single_target_detector(d0, visible_frames=frozenset({0, 1, 2, 10, 11}))
    assert detector.detect(_frame(0)) == (d0,)
    assert detector.detect(_frame(5)) == ()  # inside the dropout gap
    assert detector.detect(_frame(10)) == (d0,)


# --- the seam: FrameMeta timestamp/frame_seq survive into a downstream TrackFrame --


def test_frame_stamp_survives_into_a_downstream_track_frame() -> None:
    """Demonstrates the seam this module exists for: Detector output composes with
    the caller's own FrameMeta into a full cross-module TrackFrame, with the stamp
    untouched. This is NOT tracker logic -- track_id assignment here is a trivial
    1:1 identity for the test's own use, not ByteTrack."""
    frame = _frame(42)
    detector = MockDetector(schedule={42: (_detection(),)})
    detections = detector.detect(frame)
    track_frame = TrackFrame(
        frame=frame,
        tracks=tuple(TrackedObject(track_id=i, detection=d) for i, d in enumerate(detections)),
    )
    assert track_frame.frame.frame_seq == 42
    assert track_frame.frame.capture_ts_ns == frame.capture_ts_ns
    assert track_frame.frame is frame

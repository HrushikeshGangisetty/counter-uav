"""tools.camera_bench: CaptureMetadata validation and the pure capture analysis.

No hardware, no clock. Synthetic runs stand in for the camera; the analysis is the
same code the P0 bench will run on real metadata.
"""

from __future__ import annotations

import pytest

from tools.camera_bench import (
    CaptureMetadata,
    MetadataError,
    analyse_capture,
    read_metadata_jsonl,
    synthetic_capture_run,
    write_sample_set,
)


def _ok(**overrides: object) -> CaptureMetadata:
    base = dict(frame_index=0, width_px=1456, height_px=1088, pixel_format="SRGGB10")
    base.update(overrides)
    return CaptureMetadata(**base)  # type: ignore[arg-type]


# --- CaptureMetadata.validate ------------------------------------------------


def test_valid_metadata_has_no_problems() -> None:
    assert _ok(sequence=3, sensor_timestamp_ns=123).validate() == []


@pytest.mark.parametrize(
    "overrides,needle",
    [
        (dict(frame_index=-1), "frame_index is negative"),
        (dict(width_px=0), "frame size is not positive"),
        (dict(height_px=-2), "frame size is not positive"),
        (dict(sequence=-1), "sequence is negative"),
        (dict(sensor_timestamp_ns=-5), "sensor_timestamp_ns is negative"),
        (dict(exposure_time_us=-1), "exposure_time_us is negative"),
        (dict(analogue_gain=0.0), "analogue_gain is not positive"),
        (dict(frame_duration_us=0), "frame_duration_us is not positive"),
    ],
)
def test_malformed_metadata_is_reported(overrides: dict[str, object], needle: str) -> None:
    problems = _ok(**overrides).validate()
    assert any(needle in p for p in problems), problems


def test_require_valid_raises_on_malformed() -> None:
    with pytest.raises(MetadataError, match="frame size is not positive"):
        _ok(width_px=0).require_valid()


# --- analyse_capture ------------------------------------------------------------


def test_clean_run_reports_no_drops_and_a_stable_resolution() -> None:
    frames = synthetic_capture_run(60, fps=60.0, with_tuning=True)
    report = analyse_capture(frames)
    assert report.frame_count == 60
    assert (report.width_px, report.height_px) == (1456, 1088)
    assert report.resolution_stable is True
    assert report.pixel_format == "SRGGB10"
    assert report.dropped_frames == 0
    assert report.sequence_monotonic is True
    assert report.timestamps_monotonic is True
    assert report.measured_fps == pytest.approx(60.0, rel=1e-6)
    assert report.has_exposure_metadata is True
    assert report.has_gain_metadata is True


def test_sequence_gaps_are_counted_as_dropped_frames() -> None:
    frames = synthetic_capture_run(20, drop_before=(5, 5, 12))  # two before #5, one before #12
    report = analyse_capture(frames)
    assert report.dropped_frames == 3
    assert report.frame_count == 20
    assert report.sequence_monotonic is True


def test_missing_timestamps_leave_monotonicity_unknown() -> None:
    frames = synthetic_capture_run(10)
    stripped = [  # drop the sensor timestamps the way a stack that omits them would
        CaptureMetadata(
            frame_index=f.frame_index,
            width_px=f.width_px,
            height_px=f.height_px,
            pixel_format=f.pixel_format,
            sequence=f.sequence,
            sensor_timestamp_ns=None,
        )
        for f in frames
    ]
    report = analyse_capture(stripped)
    assert report.timestamps_monotonic is None
    assert report.measured_fps is None
    assert any("monotonicity unknown" in w for w in report.warnings)


def test_non_monotonic_timestamps_are_flagged() -> None:
    frames = [
        _ok(frame_index=0, sequence=0, sensor_timestamp_ns=100),
        _ok(frame_index=1, sequence=1, sensor_timestamp_ns=90),
        _ok(frame_index=2, sequence=2, sensor_timestamp_ns=200),
    ]
    report = analyse_capture(frames)
    assert report.timestamps_monotonic is False


def test_varying_resolution_is_flagged() -> None:
    frames = [
        _ok(frame_index=0, sequence=0, sensor_timestamp_ns=0),
        _ok(frame_index=1, sequence=1, sensor_timestamp_ns=1, width_px=640),
    ]
    report = analyse_capture(frames)
    assert report.resolution_stable is False
    assert report.width_px is None


def test_empty_run_raises() -> None:
    with pytest.raises(MetadataError, match="empty"):
        analyse_capture([])


def test_analyse_rejects_a_malformed_frame() -> None:
    with pytest.raises(MetadataError):
        analyse_capture([_ok(width_px=0)])


# --- sample set round-trip ----------------------------------------------------


def test_sample_set_round_trips(tmp_path) -> None:
    frames = synthetic_capture_run(5, with_tuning=True)
    out = write_sample_set(tmp_path / "run", frames, write_images=True)
    assert (out / "metadata.jsonl").exists()
    assert (out / "frame_0000.pgm").exists()
    loaded = read_metadata_jsonl(out / "metadata.jsonl")
    assert loaded == frames


def test_sample_set_is_byte_deterministic(tmp_path) -> None:
    frames = synthetic_capture_run(4)
    a = write_sample_set(tmp_path / "a", frames)
    b = write_sample_set(tmp_path / "b", frames)
    assert (a / "metadata.jsonl").read_bytes() == (b / "metadata.jsonl").read_bytes()
    assert (a / "frame_0003.pgm").read_bytes() == (b / "frame_0003.pgm").read_bytes()

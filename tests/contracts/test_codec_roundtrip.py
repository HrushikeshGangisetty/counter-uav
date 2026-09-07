"""Serialisation expectations: JSON keys are the attribute names, and a record
missing the stamp fields is rejected at the decode boundary."""

from __future__ import annotations

import json

import pytest

from pod_contracts.codec import to_dict, to_json_line, track_frame_from_dict
from simulation.mocks import make_track_frame


def test_roundtrip_is_lossless() -> None:
    original = make_track_frame(seq=7, track_id=42, area_fraction=0.05)
    restored = track_frame_from_dict(json.loads(to_json_line(original)))
    assert restored == original


def test_wire_keys_are_attribute_names() -> None:
    d = to_dict(make_track_frame())
    assert set(d) == {"frame", "tracks"}
    assert set(d["frame"]) == {"camera_id", "frame_seq", "capture_ts_ns", "width_px", "height_px"}


def test_timestamps_serialise_as_integer_nanoseconds() -> None:
    d = to_dict(make_track_frame(seq=3))
    assert isinstance(d["frame"]["capture_ts_ns"], int)


def test_record_without_sequence_number_is_rejected() -> None:
    d = to_dict(make_track_frame())
    del d["frame"]["frame_seq"]
    with pytest.raises(KeyError):
        track_frame_from_dict(d)


def test_record_without_capture_timestamp_is_rejected() -> None:
    d = to_dict(make_track_frame())
    del d["frame"]["capture_ts_ns"]
    with pytest.raises(KeyError):
        track_frame_from_dict(d)

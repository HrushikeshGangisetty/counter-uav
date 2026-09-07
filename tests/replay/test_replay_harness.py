"""Replay-test structure.

[PRD 2.3] "a logged flight can be replayed offline for bit-identical guidance
output, which turns tuning questions into unit tests instead of flight tests."

Today these tests prove the harness itself: fixtures decode, stamps survive the round
trip, and generation is deterministic. Once pod_geometry/guidance/state land at M2,
the same fixtures drive them and the assertions become behavioural.
"""

from __future__ import annotations

import pytest

from simulation.replay import read_track_frames, write_track_frames
from simulation.synthetic import Scenario, closing_target, generate

FIXTURES = ("closing_target", "track_dropout", "empty_sky")


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_decodes(fixtures_dir, name: str) -> None:
    frames = list(read_track_frames(fixtures_dir / "replay" / f"{name}.jsonl"))
    assert frames, f"{name} fixture is empty"
    for f in frames:
        assert f.frame.capture_ts_ns >= 0
        assert f.frame.frame_seq >= 0


@pytest.mark.parametrize("name", FIXTURES)
def test_sequence_numbers_are_monotonic(fixtures_dir, name: str) -> None:
    seqs = [f.frame.frame_seq for f in read_track_frames(fixtures_dir / "replay" / f"{name}.jsonl")]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs), "frame sequence numbers are never reused"


def test_generation_is_deterministic() -> None:
    a = list(generate(closing_target(frames=30)))
    b = list(generate(closing_target(frames=30)))
    assert a == b, "synthetic input must be reproducible or replay proves nothing"


def test_round_trip_through_a_file(tmp_path) -> None:
    original = list(generate(Scenario(name="rt", frames=10)))
    path = tmp_path / "rt.jsonl"
    assert write_track_frames(path, original) == 10
    assert list(read_track_frames(path)) == original


def test_malformed_record_is_rejected_with_a_useful_message(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(
        '{"frame": {"camera_id": 0, "frame_seq": 0, "width_px": 1, "height_px": 1}, "tracks": []}\n'
    )
    with pytest.raises(ValueError, match="capture_ts_ns and frame_seq"):
        list(read_track_frames(path))


def test_dropout_frames_carry_a_stamp_with_no_tracks(fixtures_dir) -> None:
    """A frame with nothing in it is still a frame: the tracker dropout that drives
    LOCKED -> LOST must be visible as an empty track list, not a missing record."""
    frames = list(read_track_frames(fixtures_dir / "replay" / "track_dropout.jsonl"))
    empty = [f for f in frames if not f.tracks]
    assert empty, "dropout fixture should contain frames with no tracks"
    assert all(f.frame.capture_ts_ns >= 0 for f in empty)

"""Deterministic synthetic TrackFrame generator."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from pod_contracts import BBox, Detection, FrameMeta, TrackedObject, TrackFrame


@dataclass(frozen=True, slots=True)
class Scenario:
    """A synthetic sequence description.

    All geometry here is in IMAGE space and is a stand-in for a detector, not a
    physical model. It deliberately encodes no assumption about lens, range or target
    size --- those are OD-19/OD-06 questions and inventing them here would put
    fabricated numbers into everyone's tests.
    """

    name: str
    frames: int
    fps: float = 60.0
    camera_id: int = 0
    width_px: int = 1456
    height_px: int = 1088
    track_id: int = 1
    class_id: int = 0
    class_name: str = "uav"
    confidence: float = 0.75
    start_area_fraction: float = 0.001
    end_area_fraction: float = 0.40
    start_centre: tuple[float, float] = (0.30, 0.50)
    end_centre: tuple[float, float] = (0.50, 0.50)
    start_ts_ns: int = 0
    dropout_frames: tuple[int, ...] = ()


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def generate(scenario: Scenario) -> Iterator[TrackFrame]:
    """Yield TrackFrames for a scenario. Pure and deterministic."""
    period_ns = int(round(1e9 / scenario.fps))
    for i in range(scenario.frames):
        t = 0.0 if scenario.frames <= 1 else i / (scenario.frames - 1)
        meta = FrameMeta(
            camera_id=scenario.camera_id,
            frame_seq=i,
            capture_ts_ns=scenario.start_ts_ns + i * period_ns,
            width_px=scenario.width_px,
            height_px=scenario.height_px,
        )
        if i in scenario.dropout_frames:
            yield TrackFrame(frame=meta, tracks=())
            continue
        area_frac = _lerp(scenario.start_area_fraction, scenario.end_area_fraction, t)
        area_px2 = area_frac * scenario.width_px * scenario.height_px
        side = area_px2**0.5
        cx = _lerp(scenario.start_centre[0], scenario.end_centre[0], t) * scenario.width_px
        cy = _lerp(scenario.start_centre[1], scenario.end_centre[1], t) * scenario.height_px
        track = TrackedObject(
            track_id=scenario.track_id,
            detection=Detection(
                class_id=scenario.class_id,
                class_name=scenario.class_name,
                confidence=scenario.confidence,
                bbox=BBox(x_px=cx - side / 2, y_px=cy - side / 2, w_px=side, h_px=side),
            ),
        )
        yield TrackFrame(frame=meta, tracks=(track,))


def closing_target(frames: int = 120) -> Scenario:
    """The canonical M2 sequence: a target growing from small to break-off size."""
    return Scenario(name="closing_target", frames=frames)

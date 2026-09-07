"""Detection message schema v1.0 --- the seam between perception and control.

Closes OD-17 / CF-10. The [DAY1 0] draft was
``{track_id, class, bbox, confidence, frame_ts}`` which omits the frame sequence
number required twice by [PRD 2.3, 7.2] and is therefore non-compliant. This schema
carries both, in FrameMeta, on the TrackFrame.

Owner: Person A. Producer: pod_perception (appsink callback, single writer
[PRD 7.2]). Consumers: pod_geometry, pod_state, pod_gcs.

Units: bbox in pixels, sensor-native (undistorted=False) image coordinates, origin
top-left, x right, y down. confidence in [0.0, 1.0].
Serialisation: JSON for the pod->GCS WebSocket link and for replay fixtures
(one TrackFrame per line, JSONL). Field names on the wire are the attribute names
here; the kotlinx.serialization mirror [PRD 5.5] must match them exactly.
"""

from __future__ import annotations

from dataclasses import dataclass

from .frame import FrameMeta


@dataclass(frozen=True, slots=True)
class BBox:
    """Axis-aligned bounding box in sensor-native pixels, top-left origin."""

    x_px: float
    y_px: float
    w_px: float
    h_px: float

    def area_px2(self) -> float:
        return self.w_px * self.h_px

    def centre_px(self) -> tuple[float, float]:
        return (self.x_px + self.w_px / 2.0, self.y_px + self.h_px / 2.0)

    def area_fraction(self, frame_w_px: int, frame_h_px: int) -> float:
        """Fraction of frame area, in [0,1]. This is the quantity the state machine
        compares against BBOX_AREA_TERMINAL and the break-off threshold
        [ARCH State Machine]."""
        denom = float(frame_w_px) * float(frame_h_px)
        return self.area_px2() / denom if denom > 0 else 0.0


@dataclass(frozen=True, slots=True)
class Detection:
    """One detection before track association."""

    class_id: int
    class_name: str
    confidence: float
    bbox: BBox


@dataclass(frozen=True, slots=True)
class TrackedObject:
    """One detection with a persistent ByteTrack identity [PRD 5.2].

    track_id is the basis of the entire lock mechanism; an unrecovered ID switch is a
    success-criterion failure [PRD 1.5]. OD-05 (association at 60 fps) is OPEN.
    """

    track_id: int
    detection: Detection
    frames_since_seen: int = 0


@dataclass(frozen=True, slots=True)
class TrackFrame:
    """CROSS-MODULE MESSAGE. All tracks from one frame, with its timestamp+sequence.

    Consumers reject stale data themselves via ``frame.age_ns`` rather than trusting
    the producer [PRD 2.3].
    """

    frame: FrameMeta
    tracks: tuple[TrackedObject, ...]

    def by_id(self, track_id: int) -> TrackedObject | None:
        for t in self.tracks:
            if t.track_id == track_id:
                return t
        return None

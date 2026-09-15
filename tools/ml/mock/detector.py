"""A deterministic ``Detector`` seam, so Person A/C can exercise the downstream
perception pipeline before a real model or Hailo hardware exists.

    Frame (FrameMeta)  ->  Detector  ->  Detection[]  (pod_contracts.Detection)

This is deliberately the pre-tracking seam only. ``pod_contracts.Detection`` carries
no frame reference and no track identity by design (that association is
``TrackedObject``/``TrackFrame``, assigned by ByteTrack inside the real
``hailotracker`` GStreamer element --- ``src/pod_perception/pipeline.py``). Composing
a ``Detector``'s output into a full ``TrackFrame`` for a downstream test is the
caller's job (see ``simulation.mocks.make_track_frame`` for the existing pattern);
this module does not implement tracking, per this pass's explicit scope.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from pod_contracts import Detection, FrameMeta


class Detector(Protocol):
    """Anything that turns one captured frame into zero or more detections."""

    def detect(self, frame: FrameMeta) -> tuple[Detection, ...]: ...


@dataclass(frozen=True, slots=True)
class MockDetector:
    """A scripted, deterministic stand-in for a real Hailo detector.

    ``schedule`` maps ``frame.frame_seq`` to the exact detections to return for that
    frame; a ``frame_seq`` not in ``schedule`` returns ``default`` (empty by
    default). This gives a test full control over whether and where a target
    appears, with no randomness and no model. ``detect`` never reads or mutates
    ``frame`` beyond its ``frame_seq``, so the caller's ``FrameMeta`` --- and
    therefore its ``capture_ts_ns``/``frame_seq`` --- passes through unchanged to
    whatever the caller builds next (e.g. a ``TrackedObject``/``TrackFrame``).
    """

    schedule: Mapping[int, tuple[Detection, ...]] = field(default_factory=dict)
    default: tuple[Detection, ...] = ()

    def detect(self, frame: FrameMeta) -> tuple[Detection, ...]:
        return self.schedule.get(frame.frame_seq, self.default)


def constant_detector(detections: tuple[Detection, ...]) -> MockDetector:
    """A ``MockDetector`` that returns the same detections for every frame."""
    return MockDetector(schedule={}, default=detections)


def single_target_detector(
    detection: Detection, *, visible_frames: frozenset[int] | None = None
) -> MockDetector:
    """A ``MockDetector`` producing exactly one target.

    If ``visible_frames`` is ``None``, the target is visible on every frame
    (equivalent to ``constant_detector((detection,))``). Otherwise the target
    appears only on the listed ``frame_seq`` values and is absent (empty tuple)
    everywhere else --- useful for testing dropout/re-acquisition without inventing
    a tracker.
    """
    if visible_frames is None:
        return constant_detector((detection,))
    schedule = {seq: (detection,) for seq in visible_frames}
    return MockDetector(schedule=schedule, default=())

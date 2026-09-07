"""JSON serialisation for cross-module messages. Stdlib only.

Serialisation expectations (also stated in docs/contracts.md):
  * JSON object keys are exactly the dataclass attribute names --- no renaming, no
    camelCase. The kotlinx.serialization mirror [PRD 5.5] must match these names.
  * Tuples serialise as JSON arrays; enums as their string value.
  * Timestamps are integer nanoseconds, CLOCK_MONOTONIC. Never floats: float seconds
    lose nanosecond resolution well inside the latency budget.
  * Replay fixtures are JSONL --- one message per line, in capture order.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .detection import BBox, Detection, TrackedObject, TrackFrame
from .frame import FrameMeta


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def to_dict(message: Any) -> dict[str, Any]:
    """Serialise any contract dataclass to a JSON-ready dict."""
    if not is_dataclass(message) or isinstance(message, type):
        raise TypeError(f"{type(message).__name__} is not a contract dataclass")
    return {k: _plain(v) for k, v in asdict(message).items()}


def to_json_line(message: Any) -> str:
    return json.dumps(to_dict(message), separators=(",", ":"), sort_keys=True)


def frame_meta_from_dict(d: dict[str, Any]) -> FrameMeta:
    return FrameMeta(
        camera_id=int(d["camera_id"]),
        frame_seq=int(d["frame_seq"]),
        capture_ts_ns=int(d["capture_ts_ns"]),
        width_px=int(d["width_px"]),
        height_px=int(d["height_px"]),
    )


def track_frame_from_dict(d: dict[str, Any]) -> TrackFrame:
    """Inverse of to_dict for the detection message schema v1.0.

    Raises KeyError if the capture timestamp or frame sequence number is absent ---
    which is the [PRD 7.2] requirement, enforced at the decode boundary so a
    non-compliant producer cannot get a message into the system.
    """
    tracks = []
    for t in d["tracks"]:
        det = t["detection"]
        bb = det["bbox"]
        tracks.append(
            TrackedObject(
                track_id=int(t["track_id"]),
                detection=Detection(
                    class_id=int(det["class_id"]),
                    class_name=str(det["class_name"]),
                    confidence=float(det["confidence"]),
                    bbox=BBox(
                        x_px=float(bb["x_px"]),
                        y_px=float(bb["y_px"]),
                        w_px=float(bb["w_px"]),
                        h_px=float(bb["h_px"]),
                    ),
                ),
                frames_since_seen=int(t.get("frames_since_seen", 0)),
            )
        )
    return TrackFrame(frame=frame_meta_from_dict(d["frame"]), tracks=tuple(tracks))


def track_frame_from_json_line(line: str) -> TrackFrame:
    return track_frame_from_dict(json.loads(line))

"""JSONL replay files: one contract message per line, in capture order."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from pod_contracts import TrackFrame
from pod_contracts.codec import to_json_line, track_frame_from_json_line


def write_track_frames(path: str | Path, frames: Iterable[TrackFrame]) -> int:
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for f in frames:
            fh.write(to_json_line(f))
            fh.write("\n")
            count += 1
    return count


def read_track_frames(path: str | Path) -> Iterator[TrackFrame]:
    """Decode a replay file. Rejects any record missing the capture timestamp or
    frame sequence number [PRD 7.2] --- the decoder is the enforcement point."""
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield track_frame_from_json_line(line)
            except KeyError as exc:
                raise ValueError(
                    f"{path}:{lineno}: replay record is missing required field {exc}; "
                    "every cross-module message must carry capture_ts_ns and frame_seq "
                    "[PRD 7.2]"
                ) from exc

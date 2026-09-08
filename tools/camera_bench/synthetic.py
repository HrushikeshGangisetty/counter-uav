"""Deterministic synthetic capture runs, for testing the bench tooling off-hardware.

Nothing here is a measurement. Numbers are shaped to be obviously synthetic (an
exposure of exactly 5000 us, a gain of exactly 1.0) so they can never be mistaken for
a reading from a real sensor. Mirrors the intent of ``simulation/synthetic``.

``write_sample_set`` is the only function that touches the filesystem; it writes a
JSONL of ``CaptureMetadata`` plus optional tiny ASCII-PGM placeholder images, so a
"sample set" exists to inspect and to test loaders against without a camera.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from pathlib import Path

from .metadata import CaptureMetadata

#: Obviously-synthetic tuning values used when ``with_tuning=True``. Not measurements.
_SYNTH_EXPOSURE_US = 5000
_SYNTH_ANALOGUE_GAIN = 1.0
_SYNTH_DIGITAL_GAIN = 1.0


def synthetic_capture_run(
    n_frames: int,
    *,
    fps: float = 60.0,
    width_px: int = 1456,
    height_px: int = 1088,
    pixel_format: str = "SRGGB10",
    start_timestamp_ns: int = 0,
    drop_before: Sequence[int] = (),
    with_tuning: bool = False,
) -> list[CaptureMetadata]:
    """Build a deterministic list of ``CaptureMetadata``.

    ``drop_before`` lists frame indices in front of which the pipeline "dropped"
    frames: the ``sequence`` counter skips a value there, exactly as a real dropped
    frame shows up, while ``frame_index`` stays contiguous. Repeat an index to drop
    more than one frame in the same gap.
    """
    if n_frames < 0:
        raise ValueError(f"n_frames must be >= 0, got {n_frames}")
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    period_ns = round(1e9 / fps)
    drop_before = list(drop_before)
    frames: list[CaptureMetadata] = []
    seq = 0
    for i in range(n_frames):
        seq += drop_before.count(i)  # frames the sensor produced but never delivered
        frames.append(
            CaptureMetadata(
                frame_index=i,
                width_px=width_px,
                height_px=height_px,
                pixel_format=pixel_format,
                sequence=seq,
                sensor_timestamp_ns=start_timestamp_ns + seq * period_ns,
                exposure_time_us=_SYNTH_EXPOSURE_US if with_tuning else None,
                analogue_gain=_SYNTH_ANALOGUE_GAIN if with_tuning else None,
                digital_gain=_SYNTH_DIGITAL_GAIN if with_tuning else None,
                frame_duration_us=period_ns // 1000 if with_tuning else None,
            )
        )
        seq += 1
    return frames


def _placeholder_pgm(width: int, height: int, frame_index: int) -> str:
    """A tiny ASCII (P2) greyscale image: a horizontal gradient offset by the frame
    index, so successive frames differ but are fully deterministic."""
    max_val = 255
    rows = []
    for y in range(height):
        row = [str((x * 16 + y * 4 + frame_index * 8) % (max_val + 1)) for x in range(width)]
        rows.append(" ".join(row))
    return f"P2\n{width} {height}\n{max_val}\n" + "\n".join(rows) + "\n"


def write_sample_set(
    out_dir: str | Path,
    frames: Iterable[CaptureMetadata],
    *,
    write_images: bool = True,
    image_width: int = 16,
    image_height: int = 12,
) -> Path:
    """Write ``metadata.jsonl`` (one ``CaptureMetadata`` per line) and, optionally,
    one ``frame_NNNN.pgm`` placeholder per frame into ``out_dir``. Returns ``out_dir``.

    Deterministic: the same inputs produce byte-identical output on any machine, so a
    committed sample set can be diffed in CI the way ``fixtures/replay`` is.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame_list = list(frames)
    with (out / "metadata.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for frame in frame_list:
            fh.write(json.dumps(asdict(frame), sort_keys=True) + "\n")
    if write_images:
        for frame in frame_list:
            path = out / f"frame_{frame.frame_index:04d}.pgm"
            path.write_text(
                _placeholder_pgm(image_width, image_height, frame.frame_index),
                encoding="utf-8",
                newline="\n",
            )
    return out


def read_metadata_jsonl(path: str | Path) -> list[CaptureMetadata]:
    """Load a ``metadata.jsonl`` written by ``write_sample_set``."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [CaptureMetadata(**json.loads(line)) for line in lines if line.strip()]

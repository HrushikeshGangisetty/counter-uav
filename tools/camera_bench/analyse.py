"""Turn a capture run into an inspection report. Pure --- no hardware, no I/O.

Everything here is arithmetic over a list of ``CaptureMetadata``. It reports raw
measured quantities --- frame rate, dropped-frame count, timestamp monotonicity,
whether tuning metadata was present. It does **not** pass or fail the camera: the P0
bench go/no-go thresholds are OD-A1 and are still OPEN, so applying one here would be
inventing it. ``docs/camera_validation_p0.md`` says where the numbers go.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .metadata import CaptureMetadata, MetadataError


@dataclass(frozen=True, slots=True)
class CaptureReport:
    """Summary of one capture run."""

    frame_count: int
    width_px: int | None
    height_px: int | None
    resolution_stable: bool
    pixel_format: str | None
    pixel_format_stable: bool

    #: Frames the pipeline dropped between the first and last delivered frame,
    #: counted from ``sequence`` gaps. ``None`` if no frame carried a sequence.
    dropped_frames: int | None
    sequence_monotonic: bool

    #: Strictly-increasing check on ``sensor_timestamp_ns``. ``None`` if fewer than
    #: two frames carried a timestamp.
    timestamps_monotonic: bool | None
    #: Mean delivered frame rate over the run, from first to last timestamp.
    #: ``None`` if it cannot be computed.
    measured_fps: float | None
    mean_frame_interval_ns: float | None

    has_exposure_metadata: bool
    has_gain_metadata: bool
    exposure_time_us_range: tuple[int, int] | None
    analogue_gain_range: tuple[float, float] | None

    #: Non-fatal observations (e.g. "3 frames missing a timestamp").
    warnings: tuple[str, ...] = field(default_factory=tuple)


def analyse_capture(frames: Sequence[CaptureMetadata]) -> CaptureReport:
    """Build a ``CaptureReport`` from a capture run.

    Raises ``MetadataError`` if any frame fails ``CaptureMetadata.validate`` or if
    ``frames`` is empty --- an empty run is a capture failure, not a zero-frame
    success.
    """
    if not frames:
        raise MetadataError("capture run is empty")
    for frame in frames:
        frame.require_valid()

    warnings: list[str] = []

    widths = {f.width_px for f in frames}
    heights = {f.height_px for f in frames}
    resolution_stable = len(widths) == 1 and len(heights) == 1
    width_px = next(iter(widths)) if len(widths) == 1 else None
    height_px = next(iter(heights)) if len(heights) == 1 else None
    if not resolution_stable:
        warnings.append(f"resolution varied across the run: {sorted(widths)}x{sorted(heights)}")

    formats = {f.pixel_format for f in frames if f.pixel_format}
    pixel_format_stable = len(formats) <= 1
    pixel_format = next(iter(formats)) if len(formats) == 1 else None
    if len(formats) > 1:
        warnings.append(f"pixel_format varied across the run: {sorted(formats)}")

    seqs = [f.sequence for f in frames if f.sequence is not None]
    dropped_frames: int | None
    if len(seqs) >= 2:
        deltas = [b - a for a, b in zip(seqs, seqs[1:], strict=False)]
        sequence_monotonic = all(d >= 1 for d in deltas)
        dropped_frames = sum(d - 1 for d in deltas if d >= 1)
        if not sequence_monotonic:
            warnings.append("sequence counter went backwards or repeated")
        if len(seqs) != len(frames):
            warnings.append(f"{len(frames) - len(seqs)} frames carried no sequence number")
    else:
        sequence_monotonic = True
        dropped_frames = None
        if seqs:
            warnings.append("only one frame carried a sequence number; drop count unknown")
        else:
            warnings.append("no frame carried a sequence number; drop count unknown")

    stamps = [f.sensor_timestamp_ns for f in frames if f.sensor_timestamp_ns is not None]
    timestamps_monotonic: bool | None
    measured_fps: float | None = None
    mean_frame_interval_ns: float | None = None
    if len(stamps) >= 2:
        timestamps_monotonic = all(b > a for a, b in zip(stamps, stamps[1:], strict=False))
        span_ns = stamps[-1] - stamps[0]
        if span_ns > 0:
            mean_frame_interval_ns = span_ns / (len(stamps) - 1)
            measured_fps = (len(stamps) - 1) * 1e9 / span_ns
        else:
            warnings.append("timestamp span is zero or negative; fps not computed")
        if not timestamps_monotonic:
            warnings.append("sensor_timestamp_ns is not strictly increasing")
        if len(stamps) != len(frames):
            warnings.append(f"{len(frames) - len(stamps)} frames carried no timestamp")
    else:
        timestamps_monotonic = None
        warnings.append("fewer than two frames carried a timestamp; monotonicity unknown")

    exposures = [f.exposure_time_us for f in frames if f.exposure_time_us is not None]
    gains = [f.analogue_gain for f in frames if f.analogue_gain is not None]
    exposure_time_us_range = (min(exposures), max(exposures)) if exposures else None
    analogue_gain_range = (min(gains), max(gains)) if gains else None

    return CaptureReport(
        frame_count=len(frames),
        width_px=width_px,
        height_px=height_px,
        resolution_stable=resolution_stable,
        pixel_format=pixel_format,
        pixel_format_stable=pixel_format_stable,
        dropped_frames=dropped_frames,
        sequence_monotonic=sequence_monotonic,
        timestamps_monotonic=timestamps_monotonic,
        measured_fps=measured_fps,
        mean_frame_interval_ns=mean_frame_interval_ns,
        has_exposure_metadata=bool(exposures),
        has_gain_metadata=bool(gains),
        exposure_time_us_range=exposure_time_us_range,
        analogue_gain_range=analogue_gain_range,
        warnings=tuple(warnings),
    )

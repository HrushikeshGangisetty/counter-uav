"""``CaptureMetadata`` --- what one captured frame tells us, and how to validate it.

Pure: this module has no hardware import and no I/O. ``tools.camera_bench.capture``
fills these in from ``libcamera`` request metadata on the pod;
``tools.camera_bench.synthetic`` fills them in deterministically off-hardware. Every
optional field is ``None`` when the capture stack did not report it --- a missing
value is recorded as missing, never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass


class MetadataError(ValueError):
    """A ``CaptureMetadata`` record is internally inconsistent or impossible."""


@dataclass(frozen=True, slots=True)
class CaptureMetadata:
    """Identity, timing and tuning of one captured frame.

    Attributes:
        frame_index: 0-based position of this frame within one capture run. Always
            known (it is our own counter), unlike ``sequence``.
        width_px, height_px: Frame size actually delivered by the sensor/ISP.
        pixel_format: libcamera/Bayer fourcc string, e.g. ``"SRGGB10"`` or
            ``"RGB888"``. Empty string if the stack did not report it.
        sequence: libcamera frame sequence counter. Increments per delivered frame;
            a jump of more than 1 means the pipeline dropped frames in between.
            ``None`` if unavailable.
        sensor_timestamp_ns: libcamera ``SensorTimestamp`` --- a CLOCK_MONOTONIC
            nanosecond stamp taken at start of exposure. ``None`` if unavailable.
        exposure_time_us: Reported exposure. ``None`` if unavailable.
        analogue_gain, digital_gain: Reported gains. ``None`` if unavailable.
        frame_duration_us: Reported frame-to-frame duration (the inverse of the
            instantaneous frame rate the sensor is running). ``None`` if unavailable.
    """

    frame_index: int
    width_px: int
    height_px: int
    pixel_format: str = ""
    sequence: int | None = None
    sensor_timestamp_ns: int | None = None
    exposure_time_us: int | None = None
    analogue_gain: float | None = None
    digital_gain: float | None = None
    frame_duration_us: int | None = None

    def validate(self) -> list[str]:
        """Return a list of human-readable problems; empty means the record is sane."""
        problems: list[str] = []
        if self.frame_index < 0:
            problems.append(f"frame_index is negative ({self.frame_index})")
        if self.width_px <= 0 or self.height_px <= 0:
            problems.append(f"frame size is not positive ({self.width_px}x{self.height_px})")
        if self.sequence is not None and self.sequence < 0:
            problems.append(f"sequence is negative ({self.sequence})")
        if self.sensor_timestamp_ns is not None and self.sensor_timestamp_ns < 0:
            problems.append(f"sensor_timestamp_ns is negative ({self.sensor_timestamp_ns})")
        if self.exposure_time_us is not None and self.exposure_time_us < 0:
            problems.append(f"exposure_time_us is negative ({self.exposure_time_us})")
        for name in ("analogue_gain", "digital_gain"):
            value = getattr(self, name)
            if value is not None and value <= 0.0:
                problems.append(f"{name} is not positive ({value})")
        if self.frame_duration_us is not None and self.frame_duration_us <= 0:
            problems.append(f"frame_duration_us is not positive ({self.frame_duration_us})")
        return problems

    def require_valid(self) -> None:
        """Raise ``MetadataError`` if ``validate`` found anything."""
        problems = self.validate()
        if problems:
            raise MetadataError(f"frame {self.frame_index}: " + "; ".join(problems))

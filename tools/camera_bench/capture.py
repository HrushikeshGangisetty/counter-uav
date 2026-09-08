"""Opening the real camera and pulling frames off it. Hardware-facing.

``picamera2`` / ``libcamera`` are platform packages on Raspberry Pi OS Bookworm
(``docs/developer-setup.md``), not pip dependencies. They are imported **lazily**,
inside the functions that need them, so ``import tools.camera_bench.capture`` works
on a developer laptop and the pure tooling around it stays testable. This mirrors
``pod_mavlink``'s lazy ``pymavlink`` import (decision 0021).

Nothing in this module is exercised by the test suite --- there is no camera in CI.
The tests cover the pure path (``metadata``, ``analyse``, ``synthetic``) and the
"hardware absent" error path here.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType

from .metadata import CaptureMetadata


class CameraUnavailableError(RuntimeError):
    """The camera stack (``picamera2`` / ``libcamera``) is not importable here, or no
    camera device was found."""


def _import_picamera2() -> object:
    try:
        from picamera2 import Picamera2
    except ImportError as exc:  # pragma: no cover - depends on the host
        raise CameraUnavailableError(
            "picamera2 is not installed. It is a Raspberry Pi OS platform package, "
            "not a pip dependency --- see docs/developer-setup.md. This tooling only "
            "runs on the pod."
        ) from exc
    return Picamera2


def list_cameras() -> list[dict[str, object]]:
    """Global camera info from libcamera (``Picamera2.global_camera_info()``).

    Raises ``CameraUnavailableError`` off-hardware.
    """
    picamera2 = _import_picamera2()
    return list(picamera2.global_camera_info())  # type: ignore[attr-defined]


def enumerate_modes(camera_num: int = 0) -> list[dict[str, object]]:
    """The sensor modes the driver advertises for one camera: size, format, bit
    depth, crop limits, advertised max frame duration.

    Raises ``CameraUnavailableError`` off-hardware. Which mode P0 selects is not
    decided here --- see ``docs/camera_validation_p0.md``.
    """
    picamera2 = _import_picamera2()
    cam = picamera2(camera_num)  # type: ignore[operator]
    try:
        modes: list[dict[str, object]] = []
        for mode in cam.sensor_modes:
            modes.append({key: mode.get(key) for key in sorted(mode)})
        return modes
    finally:
        cam.close()


def _metadata_from_libcamera(index: int, request_metadata: dict[str, object]) -> CaptureMetadata:
    """Map one libcamera request-metadata dict to ``CaptureMetadata``. Every field is
    pulled through ``.get`` so a stack that omits one yields ``None``, not a guess.
    ``_width`` / ``_height`` / ``_format`` are injected by ``BenchCapture.run`` from
    the active stream configuration; the rest are libcamera control names."""
    width = request_metadata.get("_width")
    height = request_metadata.get("_height")
    return CaptureMetadata(
        frame_index=index,
        width_px=int(width) if isinstance(width, int) else 0,
        height_px=int(height) if isinstance(height, int) else 0,
        pixel_format=str(request_metadata.get("_format", "")),
        sequence=_as_int(request_metadata.get("SensorSequence")),
        sensor_timestamp_ns=_as_int(request_metadata.get("SensorTimestamp")),
        exposure_time_us=_as_int(request_metadata.get("ExposureTime")),
        analogue_gain=_as_float(request_metadata.get("AnalogueGain")),
        digital_gain=_as_float(request_metadata.get("DigitalGain")),
        frame_duration_us=_as_int(request_metadata.get("FrameDuration")),
    )


def _as_int(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _as_float(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


class BenchCapture:
    """A minimal capture session over one camera, for P0 bench validation.

    Usage on the pod::

        with BenchCapture(camera_num=0) as cap:
            frames = cap.run(n_frames=600)          # ~10 s at 60 fps
            report = analyse_capture(frames)

    Off-hardware, construction succeeds but ``__enter__`` / ``start`` raise
    ``CameraUnavailableError``.
    """

    def __init__(
        self,
        camera_num: int = 0,
        *,
        size: tuple[int, int] | None = None,
        raw: bool = True,
    ) -> None:
        self.camera_num = camera_num
        self.size = size
        self.raw = raw
        self._cam: object | None = None

    def start(self) -> None:
        picamera2 = _import_picamera2()
        cam = picamera2(self.camera_num)  # type: ignore[operator]
        config_kwargs: dict[str, object] = {}
        if self.size is not None:
            config_kwargs["main"] = {"size": self.size}
        if self.raw:
            config_kwargs["raw"] = {}
        cam.configure(cam.create_video_configuration(**config_kwargs))
        cam.start()
        self._cam = cam

    def run(self, n_frames: int) -> list[CaptureMetadata]:
        if self._cam is None:
            raise CameraUnavailableError("BenchCapture.start() has not been called")
        if n_frames <= 0:
            raise ValueError(f"n_frames must be positive, got {n_frames}")
        cam = self._cam
        out: list[CaptureMetadata] = []
        for i in range(n_frames):
            request = cam.capture_request()  # type: ignore[attr-defined]
            try:
                md = dict(request.get_metadata())
                cfg = cam.camera_configuration()  # type: ignore[attr-defined]
                stream = cfg.get("raw") or cfg.get("main") or {}
                md["_width"], md["_height"] = stream.get("size", (0, 0))
                md["_format"] = stream.get("format", "")
                out.append(_metadata_from_libcamera(i, md))
            finally:
                request.release()
        return out

    def close(self) -> None:
        if self._cam is not None:
            self._cam.close()  # type: ignore[attr-defined]
            self._cam = None

    def __enter__(self) -> BenchCapture:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def save_run(out_dir: str, frames: Sequence[CaptureMetadata]) -> str:
    """Persist a real capture run's metadata via the same writer the synthetic path
    uses, so bench output and test fixtures have one format."""
    from .synthetic import write_sample_set

    return str(write_sample_set(out_dir, frames, write_images=False))

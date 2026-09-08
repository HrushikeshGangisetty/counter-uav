"""Camera bring-up and P0 bench validation for the Pi 5 + IMX296 setup.

Pure, hardware-free parts (import anywhere):
    from tools.camera_bench import (
        CaptureMetadata, analyse_capture, CaptureReport,
        synthetic_capture_run, write_sample_set,
    )

Hardware parts (pod only; raise ``CameraUnavailableError`` off-hardware):
    from tools.camera_bench import BenchCapture, enumerate_modes, list_cameras

See ``docs/camera_validation_p0.md`` for the procedure and the list of measurements
this tooling is meant to capture.
"""

from __future__ import annotations

from .analyse import CaptureReport, analyse_capture
from .capture import (
    BenchCapture,
    CameraUnavailableError,
    enumerate_modes,
    list_cameras,
    save_run,
)
from .metadata import CaptureMetadata, MetadataError
from .synthetic import read_metadata_jsonl, synthetic_capture_run, write_sample_set

__all__ = [
    "BenchCapture",
    "CameraUnavailableError",
    "CaptureMetadata",
    "CaptureReport",
    "MetadataError",
    "analyse_capture",
    "enumerate_modes",
    "list_cameras",
    "read_metadata_jsonl",
    "save_run",
    "synthetic_capture_run",
    "write_sample_set",
]

"""The hardware-facing capture layer stays importable off-hardware and fails with a
clear, actionable error rather than an ImportError traceback.

Mirrors tests/unit/test_pod_mavlink_link.py's "no pymavlink installed" path.
"""

from __future__ import annotations

import pytest

from tools.camera_bench import BenchCapture, CameraUnavailableError, enumerate_modes, list_cameras


def _picamera2_present() -> bool:
    try:
        import picamera2  # noqa: F401
    except ImportError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    _picamera2_present(),
    reason="picamera2 is installed here; the CameraUnavailableError path cannot be exercised",
)


def test_list_cameras_raises_without_the_stack() -> None:
    with pytest.raises(CameraUnavailableError, match="picamera2 is not installed"):
        list_cameras()


def test_enumerate_modes_raises_without_the_stack() -> None:
    with pytest.raises(CameraUnavailableError, match="picamera2 is not installed"):
        enumerate_modes(0)


def test_bench_capture_constructs_but_start_raises() -> None:
    cap = BenchCapture(camera_num=0, size=(1456, 1088))  # construction must not touch hardware
    with pytest.raises(CameraUnavailableError):
        cap.start()


def test_bench_capture_run_before_start_raises() -> None:
    cap = BenchCapture()
    with pytest.raises(CameraUnavailableError, match="start"):
        cap.run(10)

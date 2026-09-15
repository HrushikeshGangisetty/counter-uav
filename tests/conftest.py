"""Shared pytest fixtures. Deterministic: no clocks, no network, no hardware."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation import mocks

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def configs_dir() -> Path:
    return REPO_ROOT / "configs"


@pytest.fixture
def fixtures_dir() -> Path:
    return REPO_ROOT / "fixtures"


@pytest.fixture
def track_frame():
    return mocks.make_track_frame()


@pytest.fixture
def vehicle_state():
    return mocks.make_vehicle_state()


@pytest.fixture
def rc_state():
    return mocks.make_rc_state()


@pytest.fixture
def state_input():
    return mocks.make_state_input()


@pytest.fixture
def synthetic_calibrated_intrinsics():
    """A fully-populated pinhole ``CameraIntrinsics``, camera_id=0, 1456x1088.

    NOT a measurement --- round numbers so it can never be mistaken for OD-02
    calibration output. TEST/SIMULATION ONLY: exists to let ``pod_geometry``'s pure
    ray math execute in tests while OD-02/OD-20 are OPEN; never load this shape from
    config or a fixture file.
    """
    from pod_config import CameraIntrinsics
    from pod_contracts import DistortionModel

    def _make(camera_id: int = 0, width_px: int = 1456, height_px: int = 1088):
        return CameraIntrinsics(
            camera_id=camera_id,
            width_px=width_px,
            height_px=height_px,
            distortion_model=DistortionModel.PINHOLE_RADTAN,
            fx_px=1000.0,
            fy_px=1000.0,
            cx_px=width_px / 2,
            cy_px=height_px / 2,
            distortion_coeffs=(0.0, 0.0, 0.0, 0.0, 0.0),
            calibrated=True,
            calibration_id="synthetic-test",
            reprojection_error_px=0.0,
        )

    return _make


@pytest.fixture(autouse=True)
def _reset_config_latch():
    """pod_config is boot-time immutable; clear the latch between tests."""
    from pod_config import reset_for_tests

    reset_for_tests()
    yield
    reset_for_tests()

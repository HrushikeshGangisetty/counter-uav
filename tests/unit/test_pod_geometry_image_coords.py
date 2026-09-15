"""pod_geometry pure foundations: framing normalisation, the calibration gate, and
the ideal-pinhole camera ray. Deterministic; no hardware, no clock.

[PRD 2.3] pure modules replay bit-identically. [PRD 5.4] intrinsics gate geometry;
while OD-02 / OD-20 are open, anything needing a camera model raises.
"""

from __future__ import annotations

import pytest

from pod_config import OPEN, CameraIntrinsics, ConfigOpenError, load_pod_config
from pod_contracts import BBox, DistortionModel, FrameMeta
from pod_geometry import (
    NormalizedImagePoint,
    bbox_center_to_normalized,
    body_ray_from_camera,
    camera_ray_from_normalized,
    camera_ray_from_pixel,
    pixel_to_normalized,
    require_intrinsics,
)

W, H = 1456, 1088


def _synthetic_calibrated_intrinsics() -> CameraIntrinsics:
    """An obviously-synthetic but fully-populated pinhole model. NOT a measurement ---
    round numbers so it can never be mistaken for calibration output."""
    return CameraIntrinsics(
        camera_id=0,
        width_px=W,
        height_px=H,
        distortion_model=DistortionModel.PINHOLE_RADTAN,
        fx_px=1000.0,
        fy_px=1000.0,
        cx_px=W / 2,
        cy_px=H / 2,
        distortion_coeffs=(0.0, 0.0, 0.0, 0.0, 0.0),
        calibrated=True,
        calibration_id="synthetic-test",
        reprojection_error_px=0.0,
    )


# --- framing normalisation (no intrinsics) -----------------------------------


def test_centre_pixel_maps_to_origin() -> None:
    assert pixel_to_normalized(W / 2, H / 2, W, H) == NormalizedImagePoint(0.0, 0.0)


def test_corners_map_to_unit_square() -> None:
    assert pixel_to_normalized(0, 0, W, H) == NormalizedImagePoint(-1.0, -1.0)
    assert pixel_to_normalized(W, H, W, H) == NormalizedImagePoint(1.0, 1.0)


def test_off_centre_pixel_produces_the_correct_sign() -> None:
    right_low = pixel_to_normalized(W * 0.75, H * 0.75, W, H)
    assert right_low.nx > 0 and right_low.ny > 0
    left_high = pixel_to_normalized(W * 0.25, H * 0.25, W, H)
    assert left_high.nx < 0 and left_high.ny < 0


def test_normalisation_is_deterministic() -> None:
    a = pixel_to_normalized(123.4, 567.8, W, H)
    b = pixel_to_normalized(123.4, 567.8, W, H)
    assert a == b


def test_bbox_centre_normalisation_uses_frame_dims() -> None:
    frame = FrameMeta(camera_id=0, frame_seq=0, capture_ts_ns=0, width_px=W, height_px=H)
    bbox = BBox(x_px=W / 2 - 10, y_px=H / 2 - 10, w_px=20, h_px=20)
    assert bbox_center_to_normalized(bbox, frame) == NormalizedImagePoint(0.0, 0.0)


@pytest.mark.parametrize("w,h", [(0, 100), (100, 0), (-1, 10), (10, -1)])
def test_non_positive_dims_raise(w: int, h: int) -> None:
    with pytest.raises(ValueError, match="dimensions must be positive"):
        pixel_to_normalized(1.0, 1.0, w, h)


def test_non_finite_pixel_raises() -> None:
    with pytest.raises(ValueError, match="finite"):
        pixel_to_normalized(float("nan"), 0.0, W, H)
    with pytest.raises(ValueError, match="finite"):
        pixel_to_normalized(float("inf"), 0.0, W, H)


# --- the calibration gate ---------------------------------------------------


def test_require_intrinsics_refuses_the_shipped_open_config(configs_dir) -> None:
    cfg = load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (str(configs_dir / "camera" / "intrinsics_cam0.yaml"),),
    )
    with pytest.raises(ConfigOpenError):
        require_intrinsics(cfg.camera(0))


def test_require_intrinsics_flags_open_distortion_model() -> None:
    intr = _synthetic_calibrated_intrinsics()
    half_open = CameraIntrinsics(
        camera_id=intr.camera_id,
        width_px=intr.width_px,
        height_px=intr.height_px,
        distortion_model=OPEN,
        fx_px=intr.fx_px,
        fy_px=intr.fy_px,
        cx_px=intr.cx_px,
        cy_px=intr.cy_px,
        distortion_coeffs=intr.distortion_coeffs,
        calibrated=True,
    )
    with pytest.raises(ConfigOpenError, match="distortion_model is OPEN"):
        require_intrinsics(half_open)


def test_require_intrinsics_accepts_synthetic_calibrated_model() -> None:
    require_intrinsics(_synthetic_calibrated_intrinsics())  # must not raise


# --- ideal-pinhole camera ray --------------------------------------------------


def test_ray_at_principal_point_is_the_optical_axis() -> None:
    intr = _synthetic_calibrated_intrinsics()
    ray = camera_ray_from_pixel(intr.cx_px, intr.cy_px, intr)
    assert ray == pytest.approx((0.0, 0.0, 1.0))


def test_ray_is_a_unit_vector_and_points_right_and_down() -> None:
    intr = _synthetic_calibrated_intrinsics()
    x, y, z = camera_ray_from_pixel(intr.cx_px + 100, intr.cy_px + 200, intr)
    assert x > 0 and y > 0 and z > 0
    assert (x * x + y * y + z * z) == pytest.approx(1.0)


def test_camera_ray_from_pixel_is_deterministic() -> None:
    intr = _synthetic_calibrated_intrinsics()
    a = camera_ray_from_pixel(intr.cx_px + 100, intr.cy_px + 200, intr)
    b = camera_ray_from_pixel(intr.cx_px + 100, intr.cy_px + 200, intr)
    assert a == b


def test_camera_ray_from_normalized_matches_from_pixel() -> None:
    intr = _synthetic_calibrated_intrinsics()
    pt = pixel_to_normalized(intr.cx_px + 100, intr.cy_px + 200, intr.width_px, intr.height_px)
    assert camera_ray_from_normalized(pt, intr) == pytest.approx(
        camera_ray_from_pixel(intr.cx_px + 100, intr.cy_px + 200, intr)
    )


def test_camera_ray_refuses_open_intrinsics(configs_dir) -> None:
    cfg = load_pod_config(
        str(configs_dir / "pod.yaml"),
        str(configs_dir / "airframes" / "_template.yaml"),
        (str(configs_dir / "camera" / "intrinsics_cam0.yaml"),),
    )
    with pytest.raises(ConfigOpenError):
        camera_ray_from_pixel(10.0, 10.0, cfg.camera(0))


def test_body_ray_is_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="extrinsics are OPEN"):
        body_ray_from_camera((0.0, 0.0, 1.0))

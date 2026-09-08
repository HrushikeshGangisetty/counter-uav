"""Camera-frame ray math and the calibration gate. PURE --- no I/O, no globals.

Two things live here, kept deliberately apart from body-frame concepts:

* ``require_intrinsics`` --- the single place that asserts a ``CameraIntrinsics`` is
  usable for geometry. It raises ``ConfigOpenError`` while OD-02 (measured intrinsics)
  or OD-20 (distortion model) is open, so no caller can quietly proceed on a
  fabricated camera model.
* ``camera_ray_from_pixel`` / ``camera_ray_from_normalized`` --- back-projection of an
  image point to a unit direction vector in the **camera frame** (optical axis
  ``+z`` forward, ``+x`` right, ``+y`` down; the OpenCV convention). This is the
  ideal-pinhole step only.

⚠ These functions do **not** undistort. A real sensor-native pixel must first pass
through ``undistort_point`` (M2, blocked on OD-20) before it means anything here. In
Implementation 0 that path is unreachable with the shipped config --- every camera is
``calibrated: false`` --- so these are exercised only with synthetic calibrated
intrinsics in tests. Do not wire them into a flight path until OD-02 and OD-20 close.

⚠ The camera frame is NOT the body frame. Turning a camera-frame ray into a
body-frame line of sight needs the camera-to-body extrinsics, which depend on the
mechanical mount and are open (CF-05 / OD-15, OD-C2, OD-U2). ``body_ray_from_camera``
is therefore a stub that raises.
"""

from __future__ import annotations

import math
from typing import cast

from pod_config import CameraIntrinsics, ConfigOpenError, is_open

from .image_coords import NormalizedImagePoint


def require_intrinsics(intrinsics: CameraIntrinsics) -> None:
    """Assert that ``intrinsics`` carries a usable, measured camera model.

    Raises ``ConfigOpenError`` if the camera is not calibrated, if any of
    ``fx_px``/``fy_px``/``cx_px``/``cy_px`` is still OPEN, or if the distortion model
    has not been chosen (OD-20). This is stricter than
    ``CameraIntrinsics.require_calibrated`` on purpose: geometry needs the distortion
    model decided as well, not just the pinhole terms.
    """
    intrinsics.require_calibrated()
    if is_open(intrinsics.distortion_model):
        raise ConfigOpenError(
            f"camera {intrinsics.camera_id} distortion_model is OPEN (OD-20). "
            "pod_geometry cannot choose a model; refusing."
        )
    for name in ("fx_px", "fy_px"):
        if float(getattr(intrinsics, name)) <= 0.0:
            raise ConfigOpenError(
                f"camera {intrinsics.camera_id} {name} must be positive, "
                f"got {getattr(intrinsics, name)!r}"
            )


def _normalise(x: float, y: float, z: float) -> tuple[float, float, float]:
    norm = math.sqrt(x * x + y * y + z * z)
    if norm == 0.0:
        raise ValueError("cannot normalise a zero-length ray")
    return (x / norm, y / norm, z / norm)


def camera_ray_from_pixel(
    x_px: float, y_px: float, intrinsics: CameraIntrinsics
) -> tuple[float, float, float]:
    """Unit direction, in the camera frame, to an **undistorted** image point.

    ``(x_px, y_px)`` must already have lens distortion removed. Pure; deterministic;
    raises via ``require_intrinsics`` while the camera model is OPEN.
    """
    require_intrinsics(intrinsics)
    # require_intrinsics has proved these are measured floats, not the OPEN sentinel.
    fx = cast(float, intrinsics.fx_px)
    fy = cast(float, intrinsics.fy_px)
    cx = cast(float, intrinsics.cx_px)
    cy = cast(float, intrinsics.cy_px)
    if not (math.isfinite(x_px) and math.isfinite(y_px)):
        raise ValueError(f"pixel coordinates must be finite, got ({x_px}, {y_px})")
    return _normalise((x_px - cx) / fx, (y_px - cy) / fy, 1.0)


def camera_ray_from_normalized(
    point: NormalizedImagePoint, intrinsics: CameraIntrinsics
) -> tuple[float, float, float]:
    """``camera_ray_from_pixel`` for a point already in centred framing coordinates.

    The framing normalisation is undone with ``intrinsics.width_px``/``height_px``,
    then the pinhole back-projection runs. Same OD-02 / OD-20 gate applies.
    """
    require_intrinsics(intrinsics)
    if intrinsics.width_px <= 0 or intrinsics.height_px <= 0:
        raise ValueError(
            f"camera {intrinsics.camera_id} has no frame size "
            f"({intrinsics.width_px}x{intrinsics.height_px})"
        )
    half_w = intrinsics.width_px / 2.0
    half_h = intrinsics.height_px / 2.0
    x_px = point.nx * half_w + half_w
    y_px = point.ny * half_h + half_h
    return camera_ray_from_pixel(x_px, y_px, intrinsics)


def body_ray_from_camera(camera_ray: tuple[float, float, float]) -> tuple[float, float, float]:
    """Rotate a camera-frame ray into the vehicle body frame.

    ⚠ NOT IMPLEMENTED --- needs the camera-to-body extrinsics (mounting rotation, and
    for camera 1 the stereo baseline). Those are open: CF-05 / OD-15 (tilt bracket vs
    fixed baseline), OD-C2 (baseline distance and extrinsics), OD-U2 (the pod has no
    mechanical owner yet). M2/M4, Person C. Substituting an identity rotation here
    would be a fabricated extrinsic.
    """
    raise NotImplementedError(
        "pod_geometry.body_ray_from_camera: camera-to-body extrinsics are OPEN "
        "(CF-05 / OD-15, OD-C2, OD-U2)"
    )

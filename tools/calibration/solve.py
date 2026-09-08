"""Running the actual OpenCV calibration.

The solve needs three things this repo does not have yet: ``cv2`` (the ``vision``
extra, not installed for base dev), real board images from the actual camera+lens,
and the OD-20 decision on which distortion model to fit. So ``run_opencv_calibration``
is a stub in the house style --- it names what blocks it and raises.

``bundle_from_opencv`` is the pure part: hand it the plain numbers
``cv2.calibrateCamera`` (or ``cv2.fisheye.calibrate``) returns and it assembles a
``CalibrationBundle``. No ``cv2`` import here, so it is testable with synthetic
numbers.
"""

from __future__ import annotations

from collections.abc import Sequence

from .model import CalibrationBoard, CalibrationBundle, Matrix3x3


def bundle_from_opencv(
    *,
    camera_id: int,
    image_size: tuple[int, int],
    distortion_model: str,
    rms_reprojection_error_px: float,
    camera_matrix: Sequence[Sequence[float]],
    distortion_coeffs: Sequence[float],
    per_view_errors_px: Sequence[float],
    board: CalibrationBoard,
    calibration_id: str,
    created: str,
    tool: str,
    notes: str = "",
) -> CalibrationBundle:
    """Assemble a ``CalibrationBundle`` from OpenCV calibration outputs.

    ``camera_matrix`` is the 3x3 ``K``; ``rms_reprojection_error_px`` is the scalar
    OpenCV returns; ``per_view_errors_px`` is one RMS per calibration view (compute
    it yourself from ``projectPoints`` --- OpenCV does not return it directly).
    The result is returned with ``calibrated=True``; the caller should still run
    ``bundle.require_valid()`` and apply the OD-C1 acceptance thresholds once those
    exist.
    """
    rows = [list(map(float, r)) for r in camera_matrix]
    if len(rows) != 3 or any(len(r) != 3 for r in rows):
        raise ValueError(f"camera_matrix must be 3x3, got {camera_matrix!r}")
    k: Matrix3x3 = (
        (rows[0][0], rows[0][1], rows[0][2]),
        (rows[1][0], rows[1][1], rows[1][2]),
        (rows[2][0], rows[2][1], rows[2][2]),
    )
    return CalibrationBundle(
        camera_id=camera_id,
        image_width_px=int(image_size[0]),
        image_height_px=int(image_size[1]),
        distortion_model=distortion_model,
        camera_matrix=k,
        distortion_coeffs=tuple(float(c) for c in distortion_coeffs),
        reprojection_error_px=float(rms_reprojection_error_px),
        per_view_errors_px=tuple(float(e) for e in per_view_errors_px),
        num_views=len(per_view_errors_px),
        board=board,
        calibration_id=calibration_id,
        created=created,
        tool=tool,
        notes=notes,
        calibrated=True,
    )


def run_opencv_calibration(image_dir: str, board: CalibrationBoard) -> CalibrationBundle:
    """Detect the board in every image under ``image_dir`` and fit the intrinsics.

    ⚠ NOT IMPLEMENTED --- P0/M2, Person C. Blocked on: the ``vision`` extra (``cv2``),
    board images from the real IMX296 + lens (OD-02), and the OD-20 choice of
    distortion model (``cv2.calibrateCamera`` vs ``cv2.fisheye.calibrate``). Do not
    hard-code the model here; read it from the OD-20 decision when it lands.
    """
    raise NotImplementedError(
        "tools.calibration.solve.run_opencv_calibration: P0/M2 / Person C "
        "(needs cv2, real board images for OD-02, and the OD-20 model choice)"
    )

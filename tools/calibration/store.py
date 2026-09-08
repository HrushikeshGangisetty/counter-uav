"""Load, save and down-convert a ``CalibrationBundle``.

This is where a calibration result enters the running system:

    OpenCV calibrate  ->  CalibrationBundle  ->  to_intrinsics_config()
      ->  configs/camera/intrinsics_camN.yaml  ->  pod_config.load_pod_config()
      ->  pod_geometry via cfg.camera(n)

Until a bundle is calibrated *and* structurally clean, ``to_intrinsics_config``
emits an all-``OPEN`` runtime config with ``calibrated: false`` --- a half-finished
calibration never leaks a number into the runtime.

YAML I/O lives here and nowhere else in ``tools.calibration``.
"""

from __future__ import annotations

import os
from typing import Any

import yaml

from .model import CalibrationBoard, CalibrationBundle, CalibrationError, Matrix3x3

_OPEN_TOKENS = {"open", "tbd", "unspecified", "", None}


def _val(raw: Any) -> Any:
    if isinstance(raw, str) and raw.strip().lower() in _OPEN_TOKENS:
        return None
    return raw


def _matrix(raw: Any) -> Matrix3x3 | None:
    raw = _val(raw)
    if raw is None:
        return None
    rows: list[list[float]]
    if len(raw) == 9 and not isinstance(raw[0], (list, tuple)):
        flat = [float(x) for x in raw]
        rows = [flat[0:3], flat[3:6], flat[6:9]]
    else:
        rows = [[float(x) for x in row] for row in raw]
    if len(rows) != 3 or any(len(r) != 3 for r in rows):
        raise CalibrationError(f"camera_matrix must be 3x3 or a flat 9-list, got {raw!r}")
    return (
        (rows[0][0], rows[0][1], rows[0][2]),
        (rows[1][0], rows[1][1], rows[1][2]),
        (rows[2][0], rows[2][1], rows[2][2]),
    )


def _board(raw: Any) -> CalibrationBoard | None:
    raw = _val(raw)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise CalibrationError(f"board must be a mapping, got {raw!r}")
    return CalibrationBoard(
        pattern=str(raw.get("pattern", "")),
        rows=int(raw.get("rows", 0)),
        cols=int(raw.get("cols", 0)),
        square_size_mm=(
            None if _val(raw.get("square_size_mm")) is None else float(raw["square_size_mm"])
        ),
    )


def load_calibration(path: str) -> CalibrationBundle:
    """Read a calibration YAML into a ``CalibrationBundle``.

    Raises ``CalibrationError`` if the file is missing or not a mapping. OPEN tokens
    (``OPEN``, ``TBD``, empty, null) become ``None``. Does not itself validate the
    result --- call ``bundle.require_valid()`` for that.
    """
    if not os.path.exists(path):
        raise CalibrationError(f"calibration file not found: {path}")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise CalibrationError(f"calibration file {path} must contain a mapping at the top level")

    coeffs_raw = _val(data.get("distortion_coeffs"))
    errors_raw = _val(data.get("per_view_errors_px"))
    return CalibrationBundle(
        camera_id=int(data["camera_id"]),
        image_width_px=int(data.get("image_width_px", 0)),
        image_height_px=int(data.get("image_height_px", 0)),
        distortion_model=_val(data.get("distortion_model")),
        camera_matrix=_matrix(data.get("camera_matrix")),
        distortion_coeffs=(None if coeffs_raw is None else tuple(float(c) for c in coeffs_raw)),
        reprojection_error_px=(
            None
            if _val(data.get("reprojection_error_px")) is None
            else float(data["reprojection_error_px"])
        ),
        per_view_errors_px=(() if errors_raw is None else tuple(float(e) for e in errors_raw)),
        num_views=int(data.get("num_views", 0)),
        board=_board(data.get("board")),
        calibration_id=str(_val(data.get("calibration_id")) or ""),
        created=str(_val(data.get("created")) or ""),
        tool=str(_val(data.get("tool")) or ""),
        notes=str(_val(data.get("notes")) or ""),
        calibrated=bool(data.get("calibrated", False)),
    )


def _open_or(value: Any) -> Any:
    return "OPEN" if value is None else value


def calibration_to_dict(bundle: CalibrationBundle) -> dict[str, Any]:
    """The bundle as a plain dict for YAML, ``None`` rendered as ``OPEN``."""
    board = bundle.board
    return {
        "camera_id": bundle.camera_id,
        "image_width_px": bundle.image_width_px,
        "image_height_px": bundle.image_height_px,
        "distortion_model": _open_or(bundle.distortion_model),
        "camera_matrix": (
            "OPEN" if bundle.camera_matrix is None else [list(row) for row in bundle.camera_matrix]
        ),
        "distortion_coeffs": (
            "OPEN" if bundle.distortion_coeffs is None else list(bundle.distortion_coeffs)
        ),
        "reprojection_error_px": _open_or(bundle.reprojection_error_px),
        "per_view_errors_px": list(bundle.per_view_errors_px),
        "num_views": bundle.num_views,
        "board": (
            "OPEN"
            if board is None
            else {
                "pattern": board.pattern,
                "rows": board.rows,
                "cols": board.cols,
                "square_size_mm": _open_or(board.square_size_mm),
            }
        ),
        "calibration_id": bundle.calibration_id,
        "created": bundle.created,
        "tool": bundle.tool,
        "notes": bundle.notes,
        "calibrated": bundle.calibrated,
    }


def save_calibration(bundle: CalibrationBundle, path: str) -> None:
    """Write a ``CalibrationBundle`` to YAML."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# CalibrationBundle --- written by tools.calibration.store.save_calibration\n")
        yaml.safe_dump(calibration_to_dict(bundle), fh, sort_keys=True, default_flow_style=False)


#: Field order of configs/camera/intrinsics_camN.yaml, so a generated file reads like
#: the hand-written ones.
_INTRINSICS_OPEN_FIELDS = (
    "distortion_model",
    "fx_px",
    "fy_px",
    "cx_px",
    "cy_px",
    "distortion_coeffs",
    "reprojection_error_px",
)


def to_intrinsics_config(
    bundle: CalibrationBundle, *, lens_description: str = ""
) -> dict[str, Any]:
    """Down-convert to the ``configs/camera/intrinsics_camN.yaml`` mapping that
    ``pod_config`` loads.

    If the bundle is not acceptable for geometry (uncalibrated, or has hard
    structural problems), every measured field is ``OPEN`` and ``calibrated`` is
    ``False`` --- regardless of what partial data the bundle holds.
    """
    base: dict[str, Any] = {
        "camera_id": bundle.camera_id,
        "width_px": bundle.image_width_px,
        "height_px": bundle.image_height_px,
        "lens_description": lens_description,
    }
    if not bundle.is_acceptable_for_geometry():
        base.update({name: "OPEN" for name in _INTRINSICS_OPEN_FIELDS})
        base["calibrated"] = False
        base["calibration_id"] = ""
        return base

    base.update(
        {
            "distortion_model": bundle.distortion_model,
            "fx_px": bundle.fx_px,
            "fy_px": bundle.fy_px,
            "cx_px": bundle.cx_px,
            "cy_px": bundle.cy_px,
            "distortion_coeffs": list(bundle.distortion_coeffs or ()),
            "reprojection_error_px": bundle.reprojection_error_px,
            "calibrated": True,
            "calibration_id": bundle.calibration_id,
        }
    )
    return base


def write_intrinsics_config(
    bundle: CalibrationBundle, path: str, *, lens_description: str = ""
) -> None:
    """Write the ``pod_config`` intrinsics YAML for one camera. Overwrites ``path``."""
    payload = to_intrinsics_config(bundle, lens_description=lens_description)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "# Generated from a CalibrationBundle by "
            "tools.calibration.store.write_intrinsics_config.\n"
            "# OD-02 closes only when 'calibrated: true' here and the values below are "
            "measured.\n"
        )
        yaml.safe_dump(payload, fh, sort_keys=True, default_flow_style=False)

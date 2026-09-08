"""``CalibrationBundle`` --- the full result of an OpenCV intrinsic calibration.

This is richer than ``pod_config.CameraIntrinsics``: it keeps the evidence (per-view
reprojection errors, view count, the target used, the tool and date) that a reviewer
needs to judge a calibration, not just the numbers the runtime loads. The runtime
subset is produced from it by ``tools.calibration.store.to_intrinsics_config``.

Pure: dataclasses and validation only, no I/O, no clock. ``created`` is an ISO-8601
string the caller supplies; this module never reads the time.

House rule: absent values are ``None`` / ``()`` / ``0`` / ``""`` --- never a
plausible-looking placeholder. An uncalibrated bundle validates fine and converts to
an all-``OPEN`` runtime config; it just cannot be accepted for geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

from pod_contracts import DistortionModel

#: Distortion-coefficient counts OpenCV produces per model. pinhole_radtan is
#: (k1,k2,p1,p2[,k3[,k4,k5,k6[,s1,s2,s3,s4[,taux,tauy]]]]); fisheye is exactly
#: (k1,k2,k3,k4). These are wire/library facts, not project decisions.
_RADTAN_COEFF_COUNTS = frozenset({4, 5, 8, 12, 14})
_FISHEYE_COEFF_COUNTS = frozenset({4})

Matrix3x3 = tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]


class CalibrationError(ValueError):
    """A ``CalibrationBundle`` marked calibrated is missing or malformed."""


@dataclass(frozen=True, slots=True)
class CalibrationBoard:
    """The calibration target. ``square_size_mm`` is a *measured* physical length ---
    it is ``None`` until someone measures the printed board, and it only matters for
    metric extrinsics / stereo baseline (OD-C2), not for the pixel intrinsics."""

    pattern: str  # "checkerboard" | "charuco" | "circles" | "acircles"
    rows: int  # inner corners, not squares
    cols: int
    square_size_mm: float | None = None


@dataclass(frozen=True, slots=True)
class CalibrationBundle:
    """A camera+lens intrinsic calibration and its supporting evidence."""

    camera_id: int
    image_width_px: int
    image_height_px: int
    distortion_model: str | None = None
    camera_matrix: Matrix3x3 | None = None
    distortion_coeffs: tuple[float, ...] | None = None
    reprojection_error_px: float | None = None
    per_view_errors_px: tuple[float, ...] = ()
    num_views: int = 0
    board: CalibrationBoard | None = None
    calibration_id: str = ""
    created: str = ""  # ISO-8601, caller-supplied
    tool: str = ""
    notes: str = ""
    calibrated: bool = False

    @property
    def fx_px(self) -> float | None:
        return self.camera_matrix[0][0] if self.camera_matrix else None

    @property
    def fy_px(self) -> float | None:
        return self.camera_matrix[1][1] if self.camera_matrix else None

    @property
    def cx_px(self) -> float | None:
        return self.camera_matrix[0][2] if self.camera_matrix else None

    @property
    def cy_px(self) -> float | None:
        return self.camera_matrix[1][2] if self.camera_matrix else None

    def validate(self) -> list[str]:
        """Structural problems with this bundle. Lines beginning ``note:`` are
        advisory (they do not block acceptance); anything else is a hard problem."""
        problems: list[str] = []
        if self.image_width_px <= 0 or self.image_height_px <= 0:
            problems.append(
                f"image size is not positive ({self.image_width_px}x{self.image_height_px})"
            )
        if self.num_views < 0:
            problems.append(f"num_views is negative ({self.num_views})")
        if any(e < 0 for e in self.per_view_errors_px):
            problems.append("per_view_errors_px contains a negative value")

        if not self.calibrated:
            return problems

        # From here on the bundle claims to be a usable calibration.
        if self.distortion_model not in {m.value for m in DistortionModel}:
            problems.append(
                f"distortion_model {self.distortion_model!r} is not one of "
                f"{sorted(m.value for m in DistortionModel)} (OD-20)"
            )
        problems.extend(self._validate_matrix())
        problems.extend(self._validate_coeffs())
        if self.reprojection_error_px is None:
            problems.append("calibrated bundle has no reprojection_error_px")
        elif self.reprojection_error_px < 0:
            problems.append(f"reprojection_error_px is negative ({self.reprojection_error_px})")
        if self.num_views < 1:
            problems.append("calibrated bundle records no calibration views")
        if self.board is None:
            problems.append("calibrated bundle names no calibration board")
        elif self.board.square_size_mm is None:
            problems.append(
                "note: board.square_size_mm is unmeasured --- pixel intrinsics are "
                "still valid, but metric extrinsics / stereo baseline (OD-C2) are not"
            )
        if not self.calibration_id:
            problems.append("note: calibration_id is empty; it should identify this run")
        return problems

    def _validate_matrix(self) -> list[str]:
        m = self.camera_matrix
        if m is None:
            return ["calibrated bundle has no camera_matrix"]
        if len(m) != 3 or any(len(row) != 3 for row in m):
            return [f"camera_matrix is not 3x3 ({m!r})"]
        out: list[str] = []
        if not (m[2][0] == 0.0 and m[2][1] == 0.0 and m[2][2] == 1.0):
            out.append(f"camera_matrix bottom row is {m[2]!r}, expected (0, 0, 1)")
        if m[0][0] <= 0 or m[1][1] <= 0:
            out.append(f"fx/fy must be positive (got {m[0][0]}, {m[1][1]})")
        if not (0 <= m[0][2] <= self.image_width_px):
            out.append(f"cx {m[0][2]} is outside [0, {self.image_width_px}]")
        if not (0 <= m[1][2] <= self.image_height_px):
            out.append(f"cy {m[1][2]} is outside [0, {self.image_height_px}]")
        return out

    def _validate_coeffs(self) -> list[str]:
        coeffs = self.distortion_coeffs
        if coeffs is None:
            return ["calibrated bundle has no distortion_coeffs"]
        n = len(coeffs)
        model = self.distortion_model
        if model == DistortionModel.FISHEYE_EQUIDISTANT.value and n not in _FISHEYE_COEFF_COUNTS:
            return [f"fisheye_equidistant needs 4 coefficients, got {n}"]
        if model == DistortionModel.PINHOLE_RADTAN.value and n not in _RADTAN_COEFF_COUNTS:
            return [
                f"pinhole_radtan needs one of {sorted(_RADTAN_COEFF_COUNTS)} coefficients, got {n}"
            ]
        return []

    def hard_problems(self) -> list[str]:
        """``validate`` output with the advisory ``note:`` lines removed."""
        return [p for p in self.validate() if not p.startswith("note:")]

    def require_valid(self) -> None:
        problems = self.hard_problems()
        if problems:
            raise CalibrationError(
                f"camera {self.camera_id} calibration bundle: " + "; ".join(problems)
            )

    def is_acceptable_for_geometry(self) -> bool:
        """True only if this is a calibrated bundle with no hard structural problems.
        This is a *structural* gate, not the acceptance-threshold decision --- the
        reprojection-error / view-count thresholds are OD-C1 and still OPEN."""
        return self.calibrated and not self.hard_problems()

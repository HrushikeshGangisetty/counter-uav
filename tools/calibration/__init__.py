"""Intrinsic-calibration representation, storage and down-conversion.

    from tools.calibration import (
        CalibrationBundle, CalibrationBoard, CalibrationError,
        load_calibration, save_calibration,
        to_intrinsics_config, write_intrinsics_config,
        bundle_from_opencv,
    )

The pieces:

* ``CalibrationBundle`` / ``CalibrationBoard`` --- the full result plus its evidence,
  a pure value type (``model``).
* ``load_calibration`` / ``save_calibration`` --- YAML round-trip (``store``).
* ``to_intrinsics_config`` / ``write_intrinsics_config`` --- produce the
  ``configs/camera/intrinsics_camN.yaml`` mapping ``pod_config`` loads; emits all
  ``OPEN`` unless the bundle is calibrated and clean (``store``).
* ``bundle_from_opencv`` --- assemble a bundle from ``cv2.calibrateCamera`` outputs;
  ``run_opencv_calibration`` is the not-yet-implemented solve (``solve``).

Nothing here fabricates a calibration value. OD-02, OD-20, OD-C1 and OD-C2 stay open.
"""

from __future__ import annotations

from .model import CalibrationBoard, CalibrationBundle, CalibrationError, Matrix3x3
from .solve import bundle_from_opencv, run_opencv_calibration
from .store import (
    calibration_to_dict,
    load_calibration,
    save_calibration,
    to_intrinsics_config,
    write_intrinsics_config,
)

__all__ = [
    "CalibrationBoard",
    "CalibrationBundle",
    "CalibrationError",
    "Matrix3x3",
    "bundle_from_opencv",
    "calibration_to_dict",
    "load_calibration",
    "run_opencv_calibration",
    "save_calibration",
    "to_intrinsics_config",
    "write_intrinsics_config",
]

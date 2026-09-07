"""Line-of-sight computation. PURE --- no I/O, no threads, no globals."""

from __future__ import annotations

from pod_config import CameraIntrinsics
from pod_contracts import LineOfSight, TrackedObject, VehicleState
from pod_contracts.frame import FrameMeta


def undistort_point(x_px: float, y_px: float, intrinsics: CameraIntrinsics) -> tuple[float, float]:
    """Map a distorted pixel to normalised undistorted image coordinates.

    ⚠ NOT IMPLEMENTED --- M2, Person C.
    Blocked on OD-02 (intrinsics measured on the actual camera and lens) and OD-20
    (fisheye vs pinhole model). The model is read from
    ``intrinsics.distortion_model`` and must never be hard-coded here: the interim
    160 deg fisheye needs cv2.fisheye, a telephoto flight lens (OD-19) needs the
    standard radial-tangential model.
    """
    intrinsics.require_calibrated()
    raise NotImplementedError("pod_geometry.undistort_point: M2 / Person C (OD-02, OD-20)")


def los_from_track(
    track: TrackedObject,
    frame: FrameMeta,
    intrinsics: CameraIntrinsics,
    vehicle: VehicleState,
) -> LineOfSight:
    """Convert a tracked bounding box into a body-frame line-of-sight vector.

    ⚠ NOT IMPLEMENTED --- M2, Person C. [PRD 2.2] the pod "converts that target's
    position in the image into a desired velocity vector"; this is the first half.

    Contract when implemented:
      * pure --- same inputs give bit-identical output, so logged flights replay
        [PRD 2.3];
      * output carries ``frame`` unchanged, so the capture timestamp and sequence
        number reach downstream consumers [PRD 7.2];
      * range_m stays None until OD-06 closes. Do not substitute a proxy silently;
        set range_method to say which method produced any value;
      * budget: the whole selection/geometry/guidance/FSM stage is <1 ms typical,
        3 ms worst case [PRD 6.2]. Geometry may not become expensive.
    """
    raise NotImplementedError("pod_geometry.los_from_track: M2 / Person C (OD-02)")

"""pod_geometry --- undistortion, line-of-sight math, range estimation.

Owner of internals: Person C (Sreenija). Interface owner: Person A.
[PRD 2.3] Must never import: GStreamer, pymavlink, any I/O.
[PRD 2.3, 7.2] PURE: no I/O, no threads, no globals. A function of its inputs.

Implementation-0 status:

* ``pixel_to_normalized`` / ``bbox_center_to_normalized`` --- pure, resolution-only
  framing normalisation. Needs no calibration and is implemented.
* ``require_intrinsics`` --- the calibration gate. Implemented; raises while OD-02 /
  OD-20 are open.
* ``camera_ray_from_pixel`` / ``camera_ray_from_normalized`` --- ideal-pinhole
  back-projection to a camera-frame unit vector. Implemented, but gated by
  ``require_intrinsics`` so unreachable with the shipped ``calibrated: false`` config.
* ``undistort_point`` / ``los_from_track`` --- M2 work, blocked on OD-02 (measured
  intrinsics) and OD-20 (distortion model). They raise rather than returning a
  plausible vector [PRD 4.3] "Until this is done, every downstream number is
  fabricated."
* ``body_ray_from_camera`` --- blocked on the camera-to-body extrinsics
  (CF-05 / OD-15, OD-C2, OD-U2). Raises.
"""

from __future__ import annotations

from .camera_frame import (
    body_ray_from_camera,
    camera_ray_from_normalized,
    camera_ray_from_pixel,
    require_intrinsics,
)
from .image_coords import NormalizedImagePoint, bbox_center_to_normalized, pixel_to_normalized
from .los import los_from_track, undistort_point

__all__ = [
    "NormalizedImagePoint",
    "bbox_center_to_normalized",
    "body_ray_from_camera",
    "camera_ray_from_normalized",
    "camera_ray_from_pixel",
    "los_from_track",
    "pixel_to_normalized",
    "require_intrinsics",
    "undistort_point",
]

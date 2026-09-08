"""Image-space coordinate normalisation. PURE --- no I/O, no threads, no globals.

This is the step *before* undistortion and intrinsics. It maps a pixel in a
sensor-native frame to a **resolution-independent framing coordinate** in
``[-1, 1]`` with the origin at the geometric centre of the image, ``+x`` right and
``+y`` down (matching the ``BBox`` pixel convention in ``pod_contracts``).

⚠ These are NOT camera-normalised coordinates. Camera-normalised coordinates are
``(u - cx) / fx`` and require measured intrinsics (OD-02) and a chosen distortion
model (OD-20); producing them is ``undistort_point`` / ``los_from_track``, which are
M2 work and still raise. What is here needs no calibration: it is a pure rescale,
useful to ``pod_gcs`` overlays and to target selection regardless of lens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pod_contracts import BBox, FrameMeta


@dataclass(frozen=True, slots=True)
class NormalizedImagePoint:
    """A point in resolution-independent framing coordinates.

    ``nx`` and ``ny`` are ``0.0`` at the image centre and ``+/-1.0`` at the frame
    edges. Values outside ``[-1, 1]`` are allowed and simply mean "off frame"; this
    type does not clamp.
    """

    nx: float
    ny: float


def _check_dims(width_px: int, height_px: int) -> None:
    if width_px <= 0 or height_px <= 0:
        raise ValueError(f"frame dimensions must be positive, got {width_px}x{height_px}")


def pixel_to_normalized(
    x_px: float, y_px: float, width_px: int, height_px: int
) -> NormalizedImagePoint:
    """Map a sensor-native pixel to centred framing coordinates in ``[-1, 1]``.

    Pure and deterministic. ``x_px``/``y_px`` use the ``BBox`` convention: origin
    top-left, ``x`` right, ``y`` down. Raises ``ValueError`` on a non-positive frame
    size or a non-finite input.
    """
    _check_dims(width_px, height_px)
    if not (math.isfinite(x_px) and math.isfinite(y_px)):
        raise ValueError(f"pixel coordinates must be finite, got ({x_px}, {y_px})")
    half_w = width_px / 2.0
    half_h = height_px / 2.0
    return NormalizedImagePoint(nx=(x_px - half_w) / half_w, ny=(y_px - half_h) / half_h)


def bbox_center_to_normalized(bbox: BBox, frame: FrameMeta) -> NormalizedImagePoint:
    """Normalised framing coordinate of a bounding-box centre.

    Uses ``frame.width_px``/``frame.height_px`` for the rescale, so the point is
    consistent with the frame the detection was produced from.
    """
    cx_px, cy_px = bbox.centre_px()
    return pixel_to_normalized(cx_px, cy_px, frame.width_px, frame.height_px)

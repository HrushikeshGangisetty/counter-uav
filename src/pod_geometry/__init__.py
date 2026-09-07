"""pod_geometry --- undistortion, line-of-sight math, range estimation.

Owner of internals: Person C (Sreenija). Interface owner: Person A.
[PRD 2.3] Must never import: GStreamer, pymavlink, any I/O.
[PRD 2.3, 7.2] PURE: no I/O, no threads, no globals. A function of its inputs.

Implementation-0 status: interface only. The undistortion and LOS math are M2 work
and are blocked on OD-02 (measured intrinsics) and OD-20 (distortion model). Nothing
here fabricates a number: los_from_track raises NotImplementedError rather than
returning a plausible vector [PRD 4.3] "Until this is done, every downstream number
is fabricated."
"""

from __future__ import annotations

from .los import los_from_track, undistort_point

__all__ = ["los_from_track", "undistort_point"]

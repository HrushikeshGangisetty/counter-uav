# pod_geometry

**Owner:** Sreenija (C); interface owned by Person A · **Must never import:**
GStreamer, pymavlink, **any I/O** `[PRD 2.3]`.

**PURE**: no I/O, no threads, no globals, no clock reads. Enforced by
`tests/architecture/test_purity.py`.

Bounding box → undistorted coordinates → **body-frame line-of-sight vector**
(`LineOfSight`), consumed by `pod_guidance`.

⚠ **Blocked on OD-02.** `[PRD 5.4]`: *"Intrinsic calibration is an open blocker, not
a nice-to-have… Do this before M2, not before M4."* Until intrinsics are measured on
the actual camera **and lens**, every downstream number is fabricated — so
`undistort_point` raises rather than returning.

⚠ **OD-20:** the distortion model is read from configuration, never hard-coded. The
interim 160° fisheye needs `cv2.fisheye` (k1–k4); a telephoto flight lens flips back
to radial-tangential.

⚠ **OD-06:** `range_m` and `range_rate_ms` stay `None`. Monocular vision cannot
observe range, and stereo is effectively suspended until OD-19 restores angular
resolution. Never substitute a proxy silently — set `range_method` to say what
produced any value.

**Budget:** the whole selection/geometry/guidance/FSM stage is <1 ms typical, 3 ms
worst case `[PRD 6.2]`.

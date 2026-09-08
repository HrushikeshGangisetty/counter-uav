# 0024 — Person C's camera-validation and calibration tooling lives in `tools/`, not in a pod module

- **Date:** 2026-09-08
- **Status:** CLOSED
- **Owner:** Person C (Sreenija)
- **Source:** `[PRD 2.1, 2.3, 4.1, 5.4, 7.1, 7.2]`, `docs/architecture.md`,
  `tests/architecture/`, decisions [0010](0010-interim-fisheye-lens.md),
  [0015](0015-shared-contracts-package.md), [0021](0021-pod-mavlink-slice-boundaries.md)

**Decision.** Four structural choices, made together for the P0 camera/geometry
foundation:

1. **The hardware-facing work lives in a new top-level `tools/` package**, a peer of
   `simulation/` and `scripts/`, not under `src/pod_*`. `tools/camera_bench/` opens
   the camera, enumerates modes, captures frames and analyses a run;
   `tools/calibration/` is the representation, loading, validation and
   down-conversion of an OpenCV intrinsic calibration. `tools/` is never imported by
   any `src/pod_*` module.
2. **`picamera2` is imported lazily**, inside the functions in
   `tools/camera_bench/capture.py` that need it, exactly as `pod_mavlink` does with
   `pymavlink` ([0021](0021-pod-mavlink-slice-boundaries.md)). `import
   tools.camera_bench` works on a laptop; the pure analysis, the synthetic capture
   source and the calibration types have no hardware or `cv2` dependency at all.
3. **`pod_geometry` gains only pure foundations that need no measured number.**
   `pixel_to_normalized` / `bbox_center_to_normalized` are a resolution-only framing
   rescale. `require_intrinsics` is the calibration gate (it raises `ConfigOpenError`
   while OD-02 / OD-20 are open). `camera_ray_from_pixel` /
   `camera_ray_from_normalized` are the ideal-pinhole back-projection to a
   **camera-frame** unit vector, reachable only behind that gate — so unreachable
   with the shipped `calibrated: false` config. `undistort_point` and `los_from_track`
   are untouched and still raise; their `xfail(strict)` specs still xfail.
   `body_ray_from_camera` is a stub that raises: the camera-to-body extrinsics are
   open.
4. **A `CalibrationBundle` is a new type in `tools/`, not a change to
   `pod_config.CameraIntrinsics`.** The bundle carries the calibration *and its
   evidence* (per-view reprojection errors, view count, board, tool, date).
   `pod_config.CameraIntrinsics` stays the runtime subset, owned by Person A and
   unchanged. `tools.calibration.store.to_intrinsics_config` down-converts a bundle
   into the `configs/camera/intrinsics_camN.yaml` mapping `pod_config` already loads,
   emitting all-`OPEN` unless the bundle is calibrated *and* structurally clean.

**Reasoning.** `tests/architecture/test_purity.py` forbids I/O, threads and clock
reads in `pod_geometry`, so camera capture and file loading cannot live there.
`[PRD 2.3]` names **seven** modules and `[PRD 7.1]` forbids inserting new ones, so a
`src/pod_camera/` would read as an unsanctioned eighth architectural module. The
OpenCV solve needs the `vision` extra (`cv2`), which the base `dev` install does not
carry (`pyproject.toml`), real board images from the actual camera+lens (OD-02) and
the OD-20 model choice — none of which exist yet. Keeping this in `tools/` keeps
`import pod_*` hardware-free and keeps every fabricated-number risk on the far side of
`require_intrinsics` / `is_acceptable_for_geometry`.

**Trade-offs accepted.** `tools/` is not covered by the module-boundary tests in
`tests/architecture/` (those scan `src/pod_*` only) — mitigated because `tools/`
imports only the standard library, `yaml`, `pod_contracts` and `pod_config`, plus a
lazy `picamera2`, and it is wired into `ruff` and `mypy` via `pyproject.toml`. There
are now two places that touch camera-related code (`pod_geometry` for the pure math,
`tools/` for everything with a device or a file behind it); this entry and the module
docstrings are the map. The `camera_ray_*` functions are ahead of `undistort_point`,
so a caller could in principle feed them still-distorted pixels — the docstrings say
not to, and the gate keeps them unreachable in Implementation 0 regardless.

**Alternatives considered.**
(a) `src/pod_camera/` as an eighth `pod_*` package — rejected: `[PRD 7.1]` "No new
phases are inserted mid-execution" and the seven-module list is load-bearing for the
safety argument; an eighth module invites treating it as one.
(b) Extend `pod_config.CameraIntrinsics` with the calibration evidence fields —
rejected: it is Person A's module, `[PRD 2.3]` says it "must never import anything",
and the evidence (per-view errors, board, tool) is not runtime configuration.
(c) Put capture under `simulation/` — rejected: `simulation/` is explicitly synthetic
and deterministic (`docs/testing.md`); real hardware validation is the opposite.
(d) Implement `undistort_point` / `los_from_track` now with a chosen model — rejected:
OD-20 is open and `[PRD 5.4]` / decision 0010 are explicit that the model is
configuration, and their `xfail(strict)` specs would XPASS and turn CI red.

**Unchanged.** OD-02 (intrinsic calibration), OD-20 (distortion model), OD-06 (range),
OD-C1 (calibration acceptance thresholds), OD-C2 (stereo extrinsics), OD-A1 (P0
pass/fail thresholds), OD-04, OD-19, OD-U8 all remain OPEN. This entry adds a
destination for their results; it closes none of them. No hard invariant is touched.

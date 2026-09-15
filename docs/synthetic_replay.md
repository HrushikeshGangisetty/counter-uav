# Synthetic replay: camera -> geometry, without a camera

This describes the path that lets the team exercise frame -> detection ->
image-coordinates -> camera-frame geometry end to end while the physical camera
hardware is unavailable. It is integration and testing scaffolding, not a model of
real camera behaviour.

```
synthetic frame (FrameMeta)
    |
synthetic detection/bbox (Detection, TrackedObject, TrackFrame)
    |
image coordinates (pixel_to_normalized / bbox_center_to_normalized)   [pod_geometry]
    |
camera-frame ray (camera_ray_from_pixel / camera_ray_from_normalized) [pod_geometry, TEST-ONLY intrinsics]
    |
body-frame ray (body_ray_from_camera)   -- OPEN, raises NotImplementedError
```

Every box above already exists; this pass adds the fixtures and tests that walk the
whole chain and prove the metadata survives it, plus static-position scenarios and
this document. See [Files touched](#files-touched) at the bottom for the complete
list.

## Why this exists

`[PRD 2.3]`: *"a logged flight can be replayed offline for bit-identical guidance
output, which turns tuning questions into unit tests instead of flight tests."*
`[PRD 4.3]` calls for M2 work to start from "hand-fed synthetic detection
sequences." The physical cameras are temporarily unavailable; this path lets
`pod_geometry`'s pure functions, the JSONL replay codec, and (once it exists)
Person B's detector all be exercised without them.

## How to run it

```bash
python -m pytest tests/replay                 # replay harness + geometry chain
python -m pytest tests/unit/test_pod_geometry_image_coords.py
python scripts/make_fixtures.py                # regenerate fixtures/replay/*.jsonl
```

`make test` / `make check` run everything, including this path, as part of the
normal suite — there is no separate synthetic-only test command.

## REAL / SYNTHETIC / OPEN / HARDWARE-DEPENDENT

| Layer | Status | Notes |
|---|---|---|
| `FrameMeta`, `Detection`, `BBox`, `TrackedObject`, `TrackFrame` | **REAL** (contract) | Frozen v1.0 schema, [decision 0008](decisions/0008-detection-message-schema-v1.md). Not synthetic — this is the actual wire format. |
| `simulation.synthetic.Scenario` / `generate()` | **SYNTHETIC** | Deterministic image-space bbox trajectories. No RNG, no lens, no real target size. Lives outside `src/`. |
| `fixtures/replay/*.jsonl` | **SYNTHETIC**, generated | Committed output of `scripts/make_fixtures.py`; regeneration must be byte-identical or CI fails. |
| `pixel_to_normalized`, `bbox_center_to_normalized` | **REAL** (pure math) | No calibration needed; a resolution-independent rescale. Runs the same on synthetic or real frames. |
| `camera_ray_from_pixel`, `camera_ray_from_normalized` | **REAL** function, **OPEN** input | The pinhole math is real; it refuses to run (`ConfigOpenError`) unless given calibrated intrinsics. In production those come from OD-02; in tests they come from the synthetic fixture below. |
| `synthetic_calibrated_intrinsics` (`tests/conftest.py`) | **SYNTHETIC, TEST-ONLY** | Round-number pinhole model (`fx=fy=1000px`, centred principal point). Exists only so the ray math has something to execute against. **Must never be loaded from config or shipped as a default** — `pod_config` has no code path that would do this; the shipped `configs/camera/*.yaml` stay `calibrated: false`. |
| `body_ray_from_camera` | **OPEN**, stub | Raises `NotImplementedError` — camera-to-body extrinsics are blocked on CF-05 / OD-15, OD-C2, OD-U2 (no mechanical owner). This pass does not touch it; see [Camera-to-body seam](#camera-to-body-seam-not-built) below. |
| `undistort_point`, `los_from_track` | **OPEN**, stub | M2 / Person C, blocked on OD-02 / OD-20. Covered by `xfail(strict=True)` specs in `tests/unit/test_spec_geometry.py`. |
| Real lens FOV, distortion, stereo baseline, range | **HARDWARE-DEPENDENT** | Not modelled anywhere in this path. Interim fisheye range is a separate, already-flagged hazard (decision 0010, OD-19, OD-U8) — this replay path does not change or close it. |

## What is deterministic

Everything in the chain above the `body_ray_from_camera` stub: `generate()` takes no
clock or RNG input, `pod_geometry`'s functions are pure (no I/O, threads, globals, or
clock reads — enforced by `tests/architecture/test_purity.py`), and the JSONL codec
round-trips exactly. `tests/replay/test_geometry_replay.py::test_moving_target_stamps_are_correct_per_frame_and_deterministic`
and `::test_full_chain_ray_is_deterministic` assert this directly.

## What it intentionally does not model

- Real lens field of view, focal length, or distortion (OD-19, OD-20 are OPEN).
- Stereo baseline or camera-to-body mounting (OD-C2, CF-05/OD-15, OD-U2 are OPEN).
- Real-world target size or range — `Scenario`'s bbox growth is an arbitrary
  monotonic curve, not a physics simulation.
- Detector confidence calibration, false positives, or class confusion — synthetic
  detections are always the configured class at the configured confidence.

## Static-position scenarios added in this pass

`simulation/synthetic/generator.py` gained fixed-position presets, all reusing the
existing `Scenario` dataclass (no new fields): `target_centered`, `target_left`,
`target_right`, `target_high`, `target_low`, `target_crossing` (moves across frame),
and `target_appears` (no target, then one, via `dropout_frames` on the head of the
sequence rather than the middle or tail — appearance and disappearance are the same
mechanism). These are consumed directly by `tests/replay/test_geometry_replay.py`
rather than written out as new `.jsonl` fixtures — they exist to pin down
image-coordinate signs and the full geometry chain, not to add to the replay-harness
fixture set in `fixtures/replay/`, which already covers the closing/dropout/empty-sky
shapes the state machine needs.

## How Person B's mock detector connects

`tools/ml/mock/detector.py` defines the `Detector` seam: `FrameMeta -> Detector ->
Detection[]`, plus `MockDetector` (schedule-driven) and two convenience builders,
`constant_detector` / `single_target_detector`. It deliberately stops before
tracking — composing `Detection[]` into a `TrackedObject`/`TrackFrame` is left to the
caller (that module's own docstring says so; `pod_contracts.Detection` carries no
frame reference or track identity by design).

`simulation.synthetic.generate()` is a separate, coarser stand-in for the same seam:
it emits `TrackFrame`s directly, skipping the detector step, which is what the rest
of this file's tests build scenarios from. `test_synthetic_frame_drives_mock_detector_into_the_geometry_chain`
in `tests/replay/test_geometry_replay.py` is the bridge between the two: it takes a
`simulation.synthetic`-generated `FrameMeta`/`Detection`, drives them through the real
`MockDetector.detect()`, composes the result into a `TrackFrame` the same way
`tools/ml/mock/detector.py`'s own test does, and runs that through
`bbox_center_to_normalized` / `camera_ray_from_normalized` — proving the full
`SyntheticFrame -> MockDetector -> Detection[] -> image coordinates -> camera ray`
path this pass targets, with `frame_seq`/`capture_ts_ns` intact throughout. No
parallel detection type was added here; `pod_contracts.Detection`/`TrackedObject`/
`TrackFrame` were already the seam B's detector needed to produce.

## Camera-to-body seam (not built)

`body_ray_from_camera(camera_ray)` already exists as a signature-only stub in
`src/pod_geometry/camera_frame.py`, raising `NotImplementedError` naming the blocking
decisions (CF-05/OD-15, OD-C2, OD-U2). This pass does not implement it, add an
identity-transform default, or invent mounting angles — doing so would fabricate an
extrinsic the mechanical design has not decided. `test_body_ray_is_not_implemented`
in `tests/unit/test_pod_geometry_image_coords.py` pins the stub's current, correct
behaviour.

## How Person A eventually consumes the resulting geometry

Once OD-02/OD-20 close and `los_from_track` is implemented, `ControlLoop.tick()`
(`src/pod_mavlink/control_loop.py`) is the consumer, via the `GuidanceInput` /
`LineOfSight` contracts already defined in `pod_contracts.guidance` /
`pod_contracts.geometry`. Nothing in this pass changes that interface;
`tests/unit/test_pod_geometry_interface.py::test_los_signature_is_stable` already
locks `los_from_track`'s signature so Person A's side does not need to change when
Person C implements the body.

## Files touched

- `simulation/synthetic/generator.py`, `simulation/synthetic/__init__.py` — static
  position presets (`target_centered`, `target_left`, `target_right`, `target_high`,
  `target_low`, `target_crossing`, `target_appears`).
- `tests/conftest.py` — `synthetic_calibrated_intrinsics` fixture (TEST-ONLY).
- `tests/unit/test_pod_geometry_image_coords.py` — two small proof-point additions
  (off-centre sign, camera-ray determinism) closing gaps against the required test
  list; no production code changed.
- `tests/replay/test_geometry_replay.py` — new: the full chain, static-position
  signs, absent-target handling, invalid-metadata rejection, staleness via `age_ns`,
  and the bridge to Person B's `tools.ml.mock.detector.MockDetector`.
- `docs/synthetic_replay.md` — this file.
- `docs/testing.md` — pointer to this file.

Nothing in `pod_contracts` changed: `FrameMeta`, `Detection`, `BBox`, `TrackedObject`
and `TrackFrame` already covered everything this pass needed to represent.

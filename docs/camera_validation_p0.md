# P0 camera validation — procedure, measurements, and hand-off

**Owner:** Person C (Sreenija). **Phase:** P0 (bench), gates M1 `[PRD 7.1]`.
**Optic:** the interim 160° fisheye bundled with the innomaker IMX296 units
([decision 0010](decisions/0010-interim-fisheye-lens.md)) — *bring-up only, cannot do
counter-UAV at any useful range*. **Tooling:** `tools/camera_bench/` and
`tools/calibration/`; boundary rationale in
[decision 0024](decisions/0024-camera-validation-tooling-boundaries.md).

This document says what to run, what to measure, what stays OPEN, and what Person C
hands to A and B. It invents no requirements and no numbers: where a value is not in
a project document and has not been measured, it is OPEN
(`docs/decisions/open_decisions.md`).

## What is testable without the pod

These run on any laptop, no camera, no `libcamera`, no `cv2`:

| Capability | Entry point |
|---|---|
| Capture-run analysis: fps, dropped-frame count (sequence gaps), timestamp monotonicity, resolution/format stability, exposure & gain presence | `tools.camera_bench.analyse_capture` |
| Per-frame metadata validation | `tools.camera_bench.CaptureMetadata.validate` |
| Deterministic synthetic capture runs + sample-set writer | `tools.camera_bench.synthetic_capture_run`, `write_sample_set` |
| Calibration representation, YAML load/save/validate | `tools.calibration.CalibrationBundle`, `load_calibration` |
| Calibration → runtime config down-conversion (all-OPEN unless calibrated **and** clean) | `tools.calibration.to_intrinsics_config`, `write_intrinsics_config` |
| Pure image-coord normalisation | `pod_geometry.pixel_to_normalized`, `bbox_center_to_normalized` |
| Calibration gate + ideal-pinhole camera ray (refuses OPEN intrinsics) | `pod_geometry.require_intrinsics`, `camera_ray_from_pixel` |

## What needs the pod (P0 bench)

Requires the Pi 5, the IMX296 units, Raspberry Pi OS Bookworm with the device-tree
overlays and PCIe Gen 3 (`docs/developer-setup.md`), and `pip install -e ".[vision]"`
for the calibration solve.

### Procedure

1. **Enumerate.** `tools.camera_bench.list_cameras()` and `enumerate_modes(0)` /
   `enumerate_modes(1)`. Record every advertised sensor mode (size, packed/unpacked
   format, bit depth, advertised max frame duration). Do **not** commit to a
   production mode here — that is OD-04 territory and does not transfer off the
   interim lens (decision 0010).
2. **Sustained capture, single camera.** `BenchCapture(camera_num=0)` → `run(n)` for
   `n` covering at least several minutes at the mode under test. Feed the result to
   `analyse_capture`. Repeat for camera 1.
3. **Dual-camera capture.** Both cameras enumerated and capturing in one process;
   record whether sequence/timestamp behaviour degrades versus single-camera.
4. **Motion / global-shutter check.** Capture a moving high-contrast target; confirm
   no rolling-shutter skew. Qualitative at P0.
5. **Exposure & gain control.** Sweep exposure and analogue gain; confirm the
   requested values appear in the returned metadata and the image responds.
6. **Thermal / endurance.** Run capture across the P0 eight-hour bench window; watch
   for frame-rate decay, dropped-frame growth, driver resets (OD-11 context).
7. **Persist.** `tools.camera_bench.save_run(dir, frames)` for every run; keep the
   `CaptureReport` alongside.
8. **Calibration.** Once OD-20 (distortion model) is decided: shoot board images with
   the actual camera+lens, run the solve (`tools.calibration.solve.run_opencv_calibration`,
   not yet implemented — needs `cv2`), assemble a `CalibrationBundle`
   (`bundle_from_opencv`), `require_valid()` it, then
   `write_intrinsics_config(bundle, "configs/camera/intrinsics_cam0.yaml")`.

## Measurements Person C must obtain from the physical camera

All of these are **unmeasured today**. None has a target value in any project
document; do not assume one.

| # | Measurement | Notes / linked decision |
|---|---|---|
| 1 | Sustained delivered frame rate per camera at the mode under test | `analyse_capture().measured_fps`. Aggregate dual-camera budget is OD-03 |
| 2 | Dropped-frame rate, idle and under pipeline load | `analyse_capture().dropped_frames` (sequence gaps) |
| 3 | Timestamp source and monotonicity; offset of `SensorTimestamp` from DMA stamp | `[PRD 2.2]` stamps at DMA; confirm the libcamera stamp tracks it |
| 4 | Exposure range and step; analogue/digital gain range | metadata round-trip in step 5 |
| 5 | Global-shutter behaviour under target motion | qualitative; decision 0001 rationale |
| 6 | Thermal stability of capture over 8 h | OD-11 |
| 7 | Dual-camera simultaneous enumeration and capture stability | decision 0002 |
| 8 | **Intrinsic calibration:** `fx, fy, cx, cy`, distortion coeffs, RMS + per-view reprojection error, view count | **OD-02**, gated on **OD-20**. Belongs to camera **and** lens together — redo on the flight lens (OD-19) |
| 9 | Lens FOV as built: confirm the vendor "160°" is diagonal vs horizontal | decision 0010 — "if horizontal, every number is ~20% worse" |
| 10 | Measured usable UAV detection range vs the computed ~7–16 m | decision 0010; needs Person B's pixels-on-target floor (OD-B3) |
| 11 | Capture-stage latency contribution (exposure + readout + ISP + appsink) | feeds the `[PRD 6.2]` budget and OD-12 |
| 12 | Calibration-board square size, measured on the printed board | needed for metric extrinsics / stereo baseline only (OD-C2), not for pixel intrinsics |

## What stays OPEN after this pass

| ID | What | Owner |
|---|---|---|
| OD-02 | Intrinsic calibration values | C |
| OD-20 | Fisheye vs pinhole distortion model — decide **before** calibrating | C |
| OD-06 | Range observability (stereo suspended on the interim lens) | C, with A on the interface |
| OD-C1 | Calibration acceptance thresholds (max reprojection error, min views) and re-calibration policy | C |
| OD-C2 | Stereo baseline distance and camera-to-camera / camera-to-body extrinsics | C |
| OD-A1 | The six P0 bench go/no-go pass/fail thresholds | C with A |
| OD-04 | Letterbox vs foveated ROI crop — operational call does not transfer off the interim lens | A, with C and B |
| OD-19 / OD-U8 | Flight-lens spec / required detection range | C / unassigned |
| CF-05 / OD-15 | Tilt bracket (±15°) vs fixed stereo baseline | C raises; mechanical owner unassigned |
| — | RC channel map (`pod_config.RCChannelMap`) — not a camera item, still OPEN | A |

`tools/calibration` gives OD-C1 and OD-A1 a place to record their result
(`CalibrationBundle`, `CaptureReport`); it does not decide them. `analyse_capture`
deliberately reports raw numbers and applies no threshold.

## Artifacts Person C hands over

**To Person A (integration):**

- `configs/camera/intrinsics_cam0.yaml` / `intrinsics_cam1.yaml`, written by
  `tools.calibration.write_intrinsics_config` from a validated `CalibrationBundle` —
  `calibrated: true` only when OD-02 is genuinely closed; all-`OPEN` until then.
- `CaptureReport` + saved runs from the P0 bench, as the evidence base for OD-A1 and
  for the capture-stage share of the `[PRD 6.2]` latency budget.
- A recommended sensor mode (size / format / rate) for M1 bring-up, with the raw
  mode enumeration behind it.
- Measured capture-stage latency contribution, for OD-12 break-off-radius sizing.

**To Person B (dataset / model):**

- Confirmed sensor resolution and pixel format as delivered by the pipeline.
- Lens FOV as built (item 9) and sample frames from the real camera+lens, so dataset
  realism and the letterbox ratio (OD-04 mechanism) are grounded.
- Measured pixels-on-target samples at known distances, feeding OD-B3 (the
  pixels-on-target floor) and the decision 0010 range prediction.

## How calibration data enters the system

```
OpenCV solve (cv2, real board images)
  └─▶ tools.calibration.bundle_from_opencv(...)      -> CalibrationBundle
        └─ bundle.require_valid()                    (structure)
        └─ OD-C1 acceptance thresholds              (values — still OPEN)
        └─▶ tools.calibration.write_intrinsics_config(bundle, "configs/camera/intrinsics_camN.yaml")
              └─▶ pod_config.load_pod_config(...)    -> PodConfig.camera(n) -> CameraIntrinsics
                    └─▶ pod_geometry.require_intrinsics(...)  (raises ConfigOpenError until calibrated)
```

Until a bundle is calibrated **and** structurally clean, `write_intrinsics_config`
emits `calibrated: false` with every measured field `OPEN`, and every `pod_geometry`
entry point that needs a camera model raises `ConfigOpenError`. That is the intended
Implementation-0 state.

# Open decisions register

Imported from the Implementation 0 planning baseline (Document 4 §8) on 2026-09-07.
**Nothing here has been closed by the Implementation 0 work except where a decision
entry says so.** An item moves out of this file only when a numbered decision entry
closes it.

Status: 🔴 OPEN · 🟡 PROPOSED / DEFERRED / INTERIM · ✅ CLOSED · ⚠ BLOCKED

## Closed by Implementation 0

| ID | Decision | Entry |
|---|---|---|
| OD-17 / CF-10 | Detection message schema missing the frame sequence number | [0008](0008-detection-message-schema-v1.md) |
| OD-16 | Decision-log location, format and stewardship (steward still 🟡 to confirm) | [README](README.md) |

## Blocking, in priority order

| ID | Decision | Status | Owner | Gate | Blocked by |
|---|---|---|---|---|---|
| **OD-U8** | **Required counter-UAV detection range — never stated in any document** | 🔴 OPEN | 🔴 **UNASSIGNED** (mission/requirements, above the engineering roles) | **Before OD-19 — settle this first** | — |
| **OD-19** | **Flight-lens specification and procurement** | 🔴 OPEN | Sreenija (C) | Before M4; **hard gate before M6** | OD-U8, OD-B3, OD-10 |
| **OD-B3** | Model evaluation criteria **and the pixels-on-target floor** | 🔴 OPEN | Raghava (B) | Pixel floor **before OD-19**; rest before M6 | OD-21 |
| **OD-02** | Camera intrinsic calibration | ⚠ BLOCKED→startable | Sreenija (C) | **Before M2, not before M4** | OD-20 |
| **OD-20** | Fisheye vs pinhole distortion model | 🔴 OPEN | Sreenija (C) | Before OD-02 is performed | OD-19 flips it back |
| **OD-14 / CF-12** | Receive-only enforcement on the GCS FC link — **safety-critical, invariant 7** | 🔴 OPEN, **actively violated in the interim** | Hrushikesh (A) | Accept M2/M3 w/ expiry; **enforce before M4; hard gate before M5** | [0007](0007-interim-gcs-invariant-exception.md) — **PROPOSED, unsigned** |
| **OD-U2** | Pod mechanical ownership — enclosure, power, wiring, mounting | 🔴 OPEN | 🔴 **UNASSIGNED** | P0 / before enclosure design | — |
| **CF-05 / OD-15** | Tilt bracket (±15°) vs fixed stereo baseline | 🔴 OPEN | Sreenija (C) raises; mechanical owner unassigned | Before enclosure design | OD-U2 |

## Measured at M1

| ID | Decision | Status | Owner |
|---|---|---|---|
| OD-03 | Dual-camera inference budget (60–80 FPS is **aggregate**) | 🔴 OPEN | A, with B on model options |
| OD-04 | Letterbox vs foveated ROI crop | 🔴 OPEN — ⚠ on the interim fisheye only the **ratio** is measurable, not the operational call | A, with C and B |
| OD-08 | Software H.264 encode CPU cost | 🔴 OPEN | A |
| OD-11 | Thermal headroom under combined load | 🔴 OPEN | A |
| OD-18 / CF-09 | Power headroom: 15–20 W draw vs a 15 W converter | 🔴 OPEN | 🔴 nearest A |
| — | NMS location: on-device vs host `hailofilter` | 🔴 OPEN | B states it, A measures |

## M2 / M3

| ID | Decision | Status | Owner |
|---|---|---|---|
| OD-05 | ByteTrack association at 60 fps (ID switches mid-engagement) | 🔴 OPEN | A |
| OD-07b | ArduPilot `SRx_*` stream-rate **values** | 🔴 OPEN — the mitigation at 115200 | A |
| OD-22 | Pod-side storage: microSD or USB, capacity, sustained write rate | 🔴 OPEN | A |
| OD-12 | Per-airframe break-off radius, sized from **measured** latency | 🔴 OPEN | A |
| OD-A1 | The six P0 bench go/no-go pass/fail thresholds | 🔴 OPEN — `tools.camera_bench.analyse_capture` produces the raw figures ([0024](0024-camera-validation-tooling-boundaries.md)); the thresholds are still unset | C with A |
| OD-C1 | Calibration acceptance thresholds and re-calibration policy | 🔴 OPEN — `tools.calibration.CalibrationBundle` records the evidence ([0024](0024-camera-validation-tooling-boundaries.md)); max-reprojection / min-views thresholds still unset | C |
| OD-U9 | BREAKOFF manoeuvre duration — no document states how long the climb+yaw-away runs, so `pod_state.machine.step()` cannot implement the BREAKOFF exit yet | 🔴 OPEN | A |
| OD-U10 | LOST state's 5 s timeout exit to SEARCH — `step()` is pure/no-clock and `StateInput` carries no time-since-LOST signal, so it cannot be computed as specified. Not a safety gap: LOST always emits SILENT. See [0020](0020-state-machine-envelope-argument-and-scope.md) | 🔴 OPEN | A |
| OD-A2 | Control-thread watchdog no-progress timeout (`SafetyEnvelope.control_watchdog_timeout_ms`). `[PRD 5.5]` requires the watchdog; the timeout must be sized from the **M3 measured control-cycle distribution**, not guessed. While OPEN, `ControlSupervisor` runs unexpected-exit detection only and disables the progress watchdog (logged at start). See [0023](0023-control-thread-supervisor.md) | 🔴 OPEN | A |

## M4 and later

| ID | Decision | Status | Owner |
|---|---|---|---|
| OD-13 | RTSP video pane on Compose Multiplatform (+ gst-java vs VLCJ) | 🔴 OPEN — deferred, not solved, by the interim GCS | A |
| OD-06 | Range observability | 🔴 OPEN — stereo **effectively suspended** until OD-19 | C, with A on the interface |
| OD-C2 | Stereo baseline distance and extrinsics | 🔴 OPEN — lower priority while stereo is suspended | C |
| OD-B2 | Dataset spec: size, splits, scenarios, quality bar, versioning, hard-negative taxonomy | 🔴 OPEN (classes closed by [0009](0009-counter-uav-single-class.md)) | B |
| OD-B4 | Architecture selection across candidates | 🟡 PROPOSED | B with A |
| OD-21 | Public-dataset training programme detail | 🔴 OPEN (decided in principle, [0014](0014-public-dataset-training-now.md)) | B |

## Deferred, with a re-open trigger

| ID | Decision | Trigger |
|---|---|---|
| OD-09 | YOLOv8 AGPL-3.0 licence position ([0013](0013-yolov8-licence-deferred.md)) | Any commercial deployment |
| OD-10 | Mass budget ([0011](0011-mass-budget-deferred.md)) | Before M4 mount; on OD-19 closing |

## External / unowned

| ID | Decision | Note |
|---|---|---|
| OD-U4 | Range clearance and regulatory prerequisites for M7 | Out of scope `[PRD 1.4]`, hard gate on M7 |
| OD-U5 | Kinetic effector interface — ENGAGE ends with "kinetic event handled by host drone" | Boundary undefined |
| OD-U6 | Project schedule — **no dates or durations exist in the current baseline** | Management decision |

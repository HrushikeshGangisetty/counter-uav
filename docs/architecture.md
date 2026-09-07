# Architecture

The authority is `cuav_pod_prd.docx` v1.1, with `architecture_summary.md` v1.0 still
authoritative where the PRD does not supersede it (the state-machine table, the
performance envelope, mechanical detail). This file says how the repository realises
those documents; where the two disagree, **the documents win and the code is wrong**.

## The system in one paragraph

Photons become a RAW10 Bayer frame. MIPI CSI-2 carries it to the Pi 5's RP1 I/O
controller, which DMAs it into memory **with a capture timestamp**. The hardware ISP
debayers to NV12; a pre-processing stage produces a 640×640 tensor; the tensor crosses
PCIe to the Hailo-8L; NMS decodes detections; ByteTrack assigns persistent track IDs.
A GStreamer `tee` forks the stream — one branch encodes video for the ground station,
the other hands metadata to Python. Python selects a target, converts its bounding box
into a body-frame line-of-sight vector and then a velocity command, passes it through
a state machine and a safety governor, and — **if and only if every precondition
holds** — emits a MAVLink setpoint over the isolated UART. The flight controller
decides what to do with it. `[PRD 2.2]`

**There is no software feedback path from the FC back to the camera. The loop closes
physically, through the motion of the aircraft.** That is why *total* pipeline
latency, not any single stage, is the metric: at 150 m/s closure, 85 ms is 12.75 m of
travel.

## Modules

| Package | Owns `[PRD 2.3]` | Must never import | Owner |
|---|---|---|---|
| `pod_config` | YAML parameters, camera intrinsics, per-airframe values | Anything (see [0016](decisions/0016-pod-config-import-interpretation.md)) | Hrushikesh (A) |
| `pod_perception` | GStreamer pipeline construction, appsink callback | pymavlink, control logic | Hrushikesh (A) |
| `pod_geometry` | Undistortion, LOS math, range estimation | GStreamer, pymavlink, **any I/O** | Sreenija (C) |
| `pod_guidance` | Pursuit and proportional-navigation laws | GStreamer, pymavlink | Hrushikesh (A) |
| `pod_state` | State machine, envelope clamps, rate limits, governor | GStreamer, pymavlink | Hrushikesh (A) |
| `pod_mavlink` | **The serial port** — RX thread, governor hand-off, TX | GStreamer | Hrushikesh (A), exclusively |
| `pod_gcs` | WebSocket telemetry, RTSP video, read-only state view | pymavlink | Hrushikesh (A) |
| `pod_contracts` | *(not a PRD module)* every cross-module dataclass | everything | Hrushikesh (A) |

## The three rules that carry most of the weight `[PRD 2.3]`

1. **Perception never imports MAVLink; MAVLink never imports GStreamer.** They
   communicate only through plain dataclasses. This is what lets us swap Hailo for
   CUDA, or ArduPilot for PX4, by rewriting one module.
2. **`pod_geometry`, `pod_guidance` and `pod_state` are pure** — no I/O, no threads,
   no globals. A logged flight replays offline for bit-identical guidance output,
   *"which turns tuning questions into unit tests instead of flight tests."*
3. **Every cross-module message carries the capture timestamp and frame sequence
   number**, so any consumer can independently reject stale data.

All three are tests: `tests/architecture/`. See
[0017](decisions/0017-architecture-rules-are-tests.md).

## The seven hard invariants `[PRD 1.3]`

They are properties the system must hold **under failure**. Weakening one requires a
decision-log entry **and sign-off**.

1. The flight controller is the sole authority. The pod advises; it never commands
   directly and never overrides.
2. Pod commands are honoured only in GUIDED mode. Pilot RC input revokes pod
   influence instantly and unconditionally.
3. Loss of the pod — crash, brownout, or a heartbeat gap beyond 500 ms — does not
   cause loss of the vehicle.
4. Engagement requires **both** AI-enable RC high **AND** target-lock RC triggered.
5. Mission mode is set at takeoff and cannot be changed in flight.
6. Break-off radius is boot-loaded per-airframe config, not runtime-controllable from
   the ground station.
7. **Exactly one software module holds the serial handle to the flight controller.**

⚠ Invariant 7 is **currently not satisfied** while the interim Android GCS is in use
— [decision 0007](decisions/0007-interim-gcs-invariant-exception.md), which is
**PROPOSED and unsigned**.

## Go silent, never zero

`[PRD 4.3]` On any precondition failure the governor **stops sending setpoints**. It
does not send zero velocity: *"Zero velocity is a command, and commanding a hover may
be exactly wrong."* Silence lets ArduPilot's own tested GUIDED setpoint timeout
(~3 s) take over. There is deliberately no zero-velocity code path in `pod_state`.

## Two links to the ground `[PRD 2.4]`

| Link | Carries | Why separate |
|---|---|---|
| FC telemetry radio → GCS | attitude, position, mode, armed, RC channels | Must survive pod death. Relaying it through the pod would blind the operator at the worst moment |
| Pod → GCS (WebSocket + RTSP) | tracks, lock state, transitions, per-stage latency, annotated video | No natural representation in the standard MAVLink message set |

Collapsing them breaks a hard invariant. `pod_gcs` may not import pymavlink — enforced.

## Latency

Budget: **< 200 ms camera-to-actuation at p95, full distribution logged** `[PRD 1.5,
6.2]`. Typical total 55–85 ms; worst case 110–120 ms. Operator glass-to-glass video
latency is a **separate** figure with a ~300 ms target `[PRD 6.3]` — recording them as
one number invites optimising the control path for a problem that lives entirely in
the display.

## Out of scope, deliberately

Obstacle avoidance is a **separate pod and a separate MAVLink stream**. The only
shared resource is the FC's GUIDED setpoint input, so both cannot command
simultaneously; arbitration lives in the flight controller or a mode-priority scheme.
*"Do not design for obstacle-avoidance integration inside this pod."* `[PRD 7.3]`

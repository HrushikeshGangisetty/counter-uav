# Shared contracts

One definition per cross-module structure, in `src/pod_contracts/`. Why that package
exists and why it is not an eighth architectural module:
[decision 0015](decisions/0015-shared-contracts-package.md).

## The rule that shapes all of this

> [PRD 2.3, 7.2] **"Every cross-module message carries the capture timestamp and
> frame sequence number, so any consumer can independently reject stale data rather
> than trusting its producer."**

Every message below satisfies it either by carrying a `FrameMeta` (which holds both)
or, for `TelemetryFrame`, by carrying `capture_ts_ns` and `frame_seq` flat because its
wire form is consumed by a second language. `pod_contracts.CROSS_MODULE_MESSAGES`
lists them and `tests/contracts/test_message_stamps.py` walks that list, so the rule
is checked rather than remembered.

## Registry

| Message | Owner | Producer | Consumers | Required fields |
|---|---|---|---|---|
| `FrameMeta` | A | `pod_perception` | all | `camera_id`, `frame_seq`, `capture_ts_ns`, `width_px`, `height_px` |
| `BBox` / `Detection` / `TrackedObject` | A | `pod_perception` | `pod_geometry`, `pod_state`, `pod_gcs` | see below |
| **`TrackFrame`** (detection schema v1.0) | A | `pod_perception` appsink callback — **single writer** | `pod_geometry`, `pod_state`, `pod_gcs` | `frame`, `tracks` |
| `VehicleState` | A | `pod_mavlink` RX thread — **single writer** | `pod_geometry`, `pod_guidance`, `pod_state`, `pod_gcs` | attitude, rates, NED position/velocity, `mode`, `armed`, heartbeat stamp |
| `RCState` | A | `pod_mavlink` RX thread — **single writer** | `pod_state` | `ai_enable`, `lock_trigger`, `kill_switch` |
| `LineOfSight` | A (interface) / C (internals) | `pod_geometry` | `pod_guidance` | `frame`, `track_id`, `los_body_{x,y,z}`, `bbox_area_fraction` |
| `GuidanceInput` | A | control loop | `pod_guidance` | `frame`, `los`, `vehicle`, `law` |
| `VelocityCommand` | A | `pod_guidance` | `pod_state` | `frame`, `vx_ms`, `vy_ms`, `vz_ms`, `yaw_rate_rads` |
| `StateInput` / `StateOutput` | A | control loop / `pod_state` | `pod_state` / `pod_mavlink` | see the stamp exemption below |
| `LatencySample` | A | every stage | logging, `pod_gcs` | `frame`, `stages` |
| `TelemetryFrame` | A | `pod_gcs` | the ground station app | flat `capture_ts_ns`, `frame_seq` |
| `ModelArtifactMetadata` | A, co-authored with B | Person B, per `.hef` | `pod_perception` | see [schemas/model_artifact.md](../schemas/model_artifact.md) |

**Stamp exemption, declared not implicit.** `StateInput.frame` is `Optional` because
the state machine must still run a tick when *no frame arrived* — that is precisely
when it must go SILENT. `StateOutput`'s stamp rides on its embedded
`VelocityCommand`. Both are listed in `pod_contracts.STAMP_EXEMPT_MESSAGES` so the
exemption is reviewable.

## Units

| Quantity | Unit | Frame / convention |
|---|---|---|
| Timestamps | integer **nanoseconds** | `CLOCK_MONOTONIC`. Never float seconds; never wall-clock |
| Bounding boxes | pixels | Sensor-native, **distorted**, origin top-left, x right, y down |
| `bbox_area_fraction` | dimensionless, 0–1 | Fraction of frame area — the quantity `BBOX_AREA_TERMINAL` compares against |
| Confidence | dimensionless, 0–1 | |
| Line of sight | dimensionless unit vector | **Body frame**: x forward, y right, z down |
| Velocities | m/s | Body frame, matching `MAV_FRAME_BODY_NED` |
| Yaw rate | rad/s | Positive to the right |
| Angles | radians | |
| Position | metres | NED |
| Range | metres | `None` until OD-06 closes — **never a silent default** |

## Timestamp semantics

- `capture_ts_ns` is stamped **at DMA into memory** by the RP1 I/O controller
  `[PRD 2.2]`, not when Python first sees the frame.
- The clock is `CLOCK_MONOTONIC`, so it cannot step backwards and age arithmetic is
  always valid. It is not a calendar time and must not be logged as one.
- Every consumer computes staleness itself via `FrameMeta.age_ns(now_ns)` and rejects
  what is too old. It never trusts the producer to have done so `[PRD 2.3]`.
  The threshold is per-airframe configuration and is currently **OPEN**.

## Sequence-number semantics

- `frame_seq` increases monotonically **per `camera_id`**, from 0 at pipeline start.
- Never reused; never reset in flight.
- **Gaps are normal and are information, not errors.** The appsink runs
  `drop=true max-buffers=1` `[PRD 5.2]` — if Python falls behind, frames are dropped,
  because *"a stale frame in a closed loop is worse than no frame."* A gap says
  exactly how many.

## Serialisation

- JSON. **Object keys are exactly the Python attribute names** — no renaming, no
  camelCase. The kotlinx.serialization mirror `[PRD 5.5]` must match them.
- Tuples become arrays; enums become their string value; timestamps stay integers.
- Replay files are **JSONL**: one message per line, in capture order.
- The decoder (`pod_contracts.codec.track_frame_from_dict`) **rejects any record
  missing `capture_ts_ns` or `frame_seq`**, so a non-compliant producer cannot get
  data into the system.
- ⚠ `[PRD 5.5]` on the Python/Kotlin pair: *"The wire schema now has two definitions…
  Keep them adjacent in the repository and treat any change as touching both, or they
  will diverge."* When the Kotlin GCS is written, its mirror belongs next to
  `schemas/`.

## Changing a contract

1. Open a decision-log entry — contracts are architecture.
2. Update `pod_contracts`, `schemas/`, this file and the Kotlin mirror **together**.
3. Bump `pod_contracts.CONTRACT_VERSION`.
4. Get review from all three module owners. That friction is deliberate.

# pod_mavlink

**Owner:** Person A (Hrushikesh), exclusively · **Must never import:** GStreamer
`[PRD 2.3]`.

⚠ **Hard invariant 7** `[PRD 1.3]`: *"Exactly one software module holds the serial
handle to the flight controller. Nothing else may write to it."* `[PRD 7.2]`: *"If you
find yourself wanting a second writer, the answer is no."*

Enforced three ways: review, `tests/architecture/test_serial_ownership.py` (no other
module may import pymavlink or pyserial), and electrically by the ADuM1201 galvanic
isolator.

| Setting | Value | Source |
|---|---|---|
| Baud | **115200** | [decision 0004](../../docs/decisions/0004-mavlink-baud-115200.md) — CLOSED, reversible |
| Command rate | 20 Hz | `[PRD 1.1]` |
| Message | `SET_POSITION_TARGET_LOCAL_NED`, `MAV_FRAME_BODY_NED` | `[PRD 5.4]` |
| `type_mask` | **only** vx, vy, vz, yaw_rate — position and acceleration masked out | `[PRD 5.4]` |
| `SRx_*` streams | HEARTBEAT, ATTITUDE, LOCAL_POSITION_NED, RC_CHANNELS, VFR_HUD | `[PRD 5.4]` |

⚠ At 115200 the `SRx_*` trim is **the mitigation, not an optimisation**. A 50–200 ms
congestion spike eats the whole latency budget and *"looks exactly like an inference
stall"*. **M3 debugging order: link first, perception second.** Rate values are OPEN
(OD-07b) until measured at M3.

**Single writer:** the RX thread is the only writer of `VehicleState` and `RCState`.

**`send()` transmits nothing when the decision is SILENT.** It never substitutes a
zero-velocity setpoint.

## Status — [decision 0021](../../docs/decisions/0021-pod-mavlink-slice-boundaries.md), [decision 0022](../../docs/decisions/0022-mavlink-runtime-rx-scheduler-control-loop.md)

Pure, tested with no hardware and no pymavlink installed:
- `setpoint.py` — `build_set_position_target_local_ned()`, `MAV_FRAME_BODY_NED`,
  `SETPOINT_TYPE_MASK` (computed from `SETPOINT_TYPE_MASK_FIELDS`, never hand-written).
- `rx.py` — `initial_vehicle_state()`/`initial_rc_state()` (fail-safe defaults before
  any message has arrived) and `apply_heartbeat()`/`apply_attitude()`/
  `apply_local_position_ned()`/`rc_state_from_channels()`, the per-message-type pure
  updates the RX thread calls.

Running (decision 0022):
- `link.py` — `MavlinkLink.send()` transmits `SET_POSITION_TARGET_LOCAL_NED` when
  `decision is SEND`, nothing otherwise; `open()`/`recv()`/`close()` manage the one
  real serial handle, with `pymavlink` imported lazily so importing `pod_mavlink`
  itself never requires it.
- `rx_runtime.py` — `MavlinkRxRuntime`: one daemon thread, the **single writer** of
  `VehicleState`/`RCState` `[PRD 7.2]`. Holds no safety policy; malformed or missing
  messages keep the last good state, never fabricate a healthy one.
- `scheduler.py` — `FixedRateScheduler`: the 20 Hz driver `[PRD 1.1]`, injected
  clock/sleep, drift-free deadlines, no busy-spin.
- `control_loop.py` — `ControlLoop.tick()`: `rx.snapshot()` → `pod_state.step()` →
  `pod_state.govern()` (final authority) → `MavlinkLink.send()`. Returns a
  `CycleReport` structured log line. `PerceptionInputs` is the injected seam for the
  future perception/guidance chain; with the default (empty) source every tick
  governs to SILENT.

- `supervisor.py` — `ControlSupervisor` (decision 0023): the `[PRD 5.5]` watchdog.
  Owns the control thread; on **unexpected exit** or **no tick progress** it stops the
  scheduler and reports (`ControlHealth`, `SupervisorReport`, `on_failure`). It never
  sends, never commands, never substitutes zero velocity — silence + FC failsafe is
  the safe state. Health: `STARTING`/`RUNNING`/`HEALTHY`/`STOPPED`/`FAILED`/
  `WATCHDOG_TRIGGERED`; first terminal state wins; `stop()` is idempotent and
  race-safe.

  ⚠ The no-progress timeout is **OD-A2 OPEN** (`SafetyEnvelope.control_watchdog_timeout_ms`),
  needs M3 measured cycle latency. While OPEN the progress watchdog is **disabled**
  (logged at start) and only unexpected-exit detection runs. `simulation/` supplies a
  stand-in via `synthetic_watchdog_timeout_ns()`.

Exercised against SITL by `simulation/sitl/harness.py` — see
[`simulation/sitl/run_sitl.md`](../../simulation/sitl/run_sitl.md).

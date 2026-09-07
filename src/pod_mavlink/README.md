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

## Status — [decision 0021](../../docs/decisions/0021-pod-mavlink-slice-boundaries.md)

Implemented, pure, tested with no hardware and no pymavlink installed:
- `setpoint.py` — `build_set_position_target_local_ned()`, `MAV_FRAME_BODY_NED`,
  `SETPOINT_TYPE_MASK` (computed from `SETPOINT_TYPE_MASK_FIELDS`, never hand-written).
- `rx.py` — `initial_vehicle_state()`/`initial_rc_state()` (fail-safe defaults before
  any message has arrived) and `apply_heartbeat()`/`apply_attitude()`/
  `apply_local_position_ned()`/`rc_state_from_channels()`, the per-message-type pure
  updates the (not-yet-built) RX thread will call.
- `link.py` — `MavlinkLink.send()` transmits `SET_POSITION_TARGET_LOCAL_NED` when
  `decision is SEND`, nothing otherwise; `open()`/`close()` manage the real serial
  handle, with `pymavlink` imported lazily so importing `pod_mavlink` itself never
  requires it.

Not built this slice, and why: the **RX thread**, the **20 Hz scheduler** that would
call `send()` on a cadence, and the **M3 watchdog** (`[PRD 5.5]`) all need a live
serial port and a running process to thread against — that is SITL/M3 integration
work, once the underlying pure logic above is in place to build it on.

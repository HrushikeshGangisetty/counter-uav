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

# Running the pod runtime against ArduPilot SITL

Status: usable now for the **software path** (RX thread → 20 Hz scheduler →
`pod_state` → `MavlinkLink.send()`). A full pursuit/break-off flight is still **M2**
and needs the perception/guidance chain, which does not exist yet.

See [decision 0022](../../docs/decisions/0022-mavlink-runtime-rx-scheduler-control-loop.md)
for what this exercises and what it deliberately does not.

## 1. Install the `sitl` extra

```bash
pip install -e '.[sitl]'
```

This brings in `pymavlink` and `MAVProxy`. Without it, `SitlHarness` and
`tests/unit/test_pod_mavlink_sitl_harness.py` skip (the pure runtime tests still run).

## 2. Start ArduPilot SITL (separate terminal)

Not vendored here — clone `ArduPilot/ardupilot`, run
`Tools/environment_install/install-prereqs-ubuntu.sh`, then:

```bash
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter --console --map
```

Default MAVLink out is `udp:127.0.0.1:14550`, which matches `sitl.yaml`'s
`connection` placeholder. `home` and `ardupilot_root` in `sitl.yaml` stay `OPEN`
(no test-site coordinates exist in any document) and are not read by the harness.

## 3. Run the pod runtime

```python
from simulation.sitl.harness import (
    SitlHarness,
    constant_pursuit_source,
    synthetic_watchdog_timeout_ns,
)

with SitlHarness(
    command_source=constant_pursuit_source(),
    # ⚠ NOT the production value. OD-A2 is OPEN. Omit this and only the
    # unexpected-exit watchdog runs; pass it to also exercise the stall path.
    watchdog_timeout_ns=synthetic_watchdog_timeout_ns(),
) as h:
    health = h.run(duration_s=5.0)
    print("health", health, "ticks", h.scheduler.tick_count, "rx seen", h.rx.messages_seen)
```

Each cycle logs one structured line via `logging` (`pod_mavlink.control_loop`):
`state`, `decision`, `reason`, `sent`, `hb_ok`, `tick_ms`. The supervisor
(`pod_mavlink.supervisor`) logs control-loop start/stop, health transitions and any
watchdog trip; `h.run()` returns the final `ControlHealth` and `h.last_failure`
holds the `SupervisorReport` if it failed.

## 4. Drive the state machine from MAVProxy

RC comes from the simulator, never from the pod. In the MAVProxy console:

```
mode GUIDED
arm throttle
rc 6 2000      # ai-enable channel high   (synthetic map in harness.py: ch6/7/8)
rc 7 2000      # lock-trigger high
```

With `mode GUIDED`, heartbeat healthy, `rc 6`/`rc 7` high and `rc 8` low, a governed
`SEND` will reach `MavlinkLink.send()` and a `SET_POSITION_TARGET_LOCAL_NED` appears
on the link. Drop `rc 6`, change mode, or raise `rc 8` (kill) and the pod goes
**silent** — no zero-velocity setpoint — and ArduPilot's ~3 s GUIDED timeout takes
over. That is the behaviour the governor relies on `[PRD 4.3, 5.4]`.

## 5. Shut down

`SitlHarness.stop()` (or leaving the `with` block) stops the supervisor (which stops
the scheduler and joins the control + watchdog threads), joins the RX
thread and closes the link. Then `Ctrl-C` the `sim_vehicle.py` terminal.

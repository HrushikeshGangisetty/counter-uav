# ArduPilot SITL environment

**Status: the software path runs; a full flight does not.**
`harness.py` (`SitlHarness`) wires the `pod_mavlink` RX thread, the 20 Hz scheduler,
`pod_state` and `MavlinkLink.send()` to a MAVLink endpoint — see
[`run_sitl.md`](run_sitl.md) and
[decision 0022](../../docs/decisions/0022-mavlink-runtime-rx-scheduler-control-loop.md).
A full pursuit/break-off flight still belongs to **M2** and needs the
perception/guidance chain, which does not exist yet. `home` and `ardupilot_root` in
`sitl.yaml` stay `OPEN` and are not read by the harness.

## External dependencies — documented, not auto-installed

Deliberately not wrapped in a setup script. A hidden installer that half-works on one
laptop is worse than four documented commands, and the ArduPilot build environment is
too large and too version-sensitive to vendor here.

| Dependency | Why | Notes |
|---|---|---|
| ArduPilot source + `sim_vehicle.py` | SITL runs the *actual* flight code, so behaviour transfers [PRD 5.4] | Clone `ArduPilot/ardupilot`, run `Tools/environment_install/install-prereqs-ubuntu.sh`, then `./waf configure --board sitl && ./waf copter` |
| MAVProxy | Message-level inspection, stream-rate tuning [PRD 5.4] | `pip install MAVProxy` |
| pymavlink | Pod-side MAVLink [PRD 5.4] | `pip install -e '.[sitl]'` |

Frame: **copter** [PRD 5.4], [DAY1 1].

## Entry points

| File | Purpose | Status |
|---|---|---|
| `sitl.yaml` | Connection string, frame, home location, speedup | `connection` used; `home`/`ardupilot_root` still `OPEN`, unused |
| `harness.py` | `SitlHarness` — opens the link, starts the RX thread, drives `ControlLoop` at 20 Hz | usable for the software path |
| `run_sitl.md` | The launch recipe once ArduPilot is installed locally | usable |

## What M2 must demonstrate here

- Simulated aircraft completes a full pursuit and break-off driven **only** by
  synthetic detections [PRD 4.3].
- Every defined failure mode leaves the pod **silent**, not commanding: heartbeat
  loss, mode change out of GUIDED, kill-switch assertion, stale frame rejection
  [PRD 4.3].
- GUIDED velocity setpoints time out after ~3 s of silence and the FC's own failsafe
  takes over — this is the behaviour the governor deliberately relies on [PRD 5.4].

# ArduPilot SITL environment

**Status: scaffold only. Nothing here launches a simulator yet.**
Standing SITL up is task **A-P1-1** and belongs to **M2**; Implementation 0 provides
the directory, the placeholders and the entry points, not the control system.

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

## Entry points (M2 — not implemented)

| File | Purpose | Phase |
|---|---|---|
| `sitl.yaml` | Connection string, frame, home location, speedup | placeholders now |
| `run_sitl.md` | The launch recipe once ArduPilot is installed locally | M2 |

## What M2 must demonstrate here

- Simulated aircraft completes a full pursuit and break-off driven **only** by
  synthetic detections [PRD 4.3].
- Every defined failure mode leaves the pod **silent**, not commanding: heartbeat
  loss, mode change out of GUIDED, kill-switch assertion, stale frame rejection
  [PRD 4.3].
- GUIDED velocity setpoints time out after ~3 s of silence and the FC's own failsafe
  takes over — this is the behaviour the governor deliberately relies on [PRD 5.4].

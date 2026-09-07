# CLAUDE.md — non-negotiables for this repository

Read this before changing anything here. It exists so that a future session, human or
AI, cannot erode a safety property by accident. **When this file and a project
document disagree, the document wins** — `cuav_pod_prd.docx` v1.1 first, then the
non-superseded parts of `architecture_summary.md` v1.0.

## What this project is

A **companion computer that advises a flight controller**. It is not a flight
controller. A bug here should end with the pod going quiet and the aircraft flying on.

## Seven hard invariants `[PRD 1.3]` — never weaken one without a signed decision entry

1. The FC is the sole authority. The pod advises; it never commands directly and
   never overrides.
2. Pod commands are honoured only in GUIDED mode. Pilot RC input revokes pod
   influence instantly and unconditionally.
3. Loss of the pod — crash, brownout, heartbeat gap > 500 ms — does not cause loss of
   the vehicle.
4. Engagement requires **both** AI-enable RC high **AND** target-lock RC triggered.
5. Mission mode is set at takeoff and cannot be changed in flight.
6. Break-off radius is boot-loaded per-airframe config, not runtime-controllable from
   the GCS.
7. **Exactly one software module holds the serial handle to the FC.** `pod_mavlink`.

`[PRD 1.3]`: *"Any change that weakens one of these requires a decision-log entry and
sign-off."* ⚠ Invariant 7 is currently **not satisfied** in the interim — decision
0007, PROPOSED and unsigned.

## Architecture rules that are not style preferences

- **Perception never imports MAVLink. MAVLink never imports GStreamer.**
- **`pod_geometry`, `pod_guidance`, `pod_state` are pure**: no I/O, no threads, no
  globals, **no clock reads** — `now_ns` is passed in. This is what makes a logged
  flight replay to bit-identical output.
- **Every cross-module message carries a capture timestamp and a frame sequence
  number.** Defined once, in `pod_contracts`. Never copy a structure into a module.
- **Single writer per shared field**: `VehicleState`/`RCState` only by the MAVLink RX
  thread; `TrackFrame` only by the appsink callback.
- **Safety-critical config is boot-time immutable**: break-off radius, velocity
  envelopes, mission mode. Loaded from YAML at startup; not changeable from the GUI.

These are enforced in `tests/architecture/`. **If a test there fails, fix the code —
do not edit the rule.** Editing `tests/architecture/rules.py` is editing the
architecture and requires a decision entry.

## Behavioural rules that are easy to get wrong

- **Go silent, never zero.** On any precondition failure, stop sending setpoints. Do
  **not** send zero velocity: *"Zero velocity is a command, and commanding a hover may
  be exactly wrong."* Silence lets ArduPilot's tested ~3 s GUIDED timeout take over.
  There is no zero-velocity code path in `pod_state`, and none may be added.
- **The appsink is `drop=true max-buffers=1`.** Drop frames, never queue them: *"a
  stale frame in a closed loop is worse than no frame."*
- **Setpoints are `SET_POSITION_TARGET_LOCAL_NED` in `MAV_FRAME_BODY_NED`** with the
  `type_mask` enabling **only** vx, vy, vz and yaw_rate. Position and acceleration
  bits masked out.
- **The video branch is sacrificial.** Cap at 30 fps, downscale before encoding, and
  verify it starves before the control path does.
- **Consumers reject stale data themselves.** Never trust a producer's freshness.

## The house rule about numbers

**If a value is not stated in a project document and has not been measured, it is
`OPEN`.** `pod_config` represents OPEN as a sentinel and raises `ConfigOpenError` at
the point of use. Do not substitute a plausible default anywhere — not in config, not
in a test, not in a docstring. A plausible number becomes indistinguishable from a
measured one within weeks, and this project has already paid twice for reversals it
could not reconstruct.

Corollary: **do not invent architecture or requirements.** If a document does not
cover it, write `OPEN`, name an owner, and put it in
`docs/decisions/open_decisions.md`.

## Phase discipline `[PRD 7.1]`

Eight sequential phases: P0, M1–M7. *"No phase begins until the previous phase's exit
gate is demonstrated, not merely believed. No new phases are inserted mid-execution."*
Do not implement M1/M2/M3 functionality because it is convenient. Stubs raise
`NotImplementedError` naming their phase and owner — that is the design, not a gap to
fill in passing.

## Decision log

`docs/decisions/`. Every entry: **date, decision, reasoning, trade-offs accepted,
alternatives considered.** Append-only; a decision is reversed by a new entry.

## Currently live hazards

| Hazard | Where |
|---|---|
| Interim 160° fisheye gives ~7–16 m usable UAV detection range — counter-UAV is not achievable on it | decision 0010, OD-19, OD-U8 |
| Hard invariant 7 unsatisfied while the interim Android GCS is used; exception unsigned | decision 0007, OD-14 |
| Intrinsics are OPEN — all geometry output is fabricated until OD-02 closes | `configs/camera/`, OD-02 |
| At 115200 baud a 50–200 ms congestion spike eats the whole latency budget and looks exactly like an inference stall. **M3 debugging order: link first, perception second** | decision 0004, OD-07b |
| Pod mechanical (enclosure, power, wiring) has **no owner** | OD-U2 |

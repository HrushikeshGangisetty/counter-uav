# 0022 — `pod_mavlink` runtime: RX thread, 20 Hz scheduler, control loop live in `pod_mavlink`

- **Date:** 2026-09-07
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 1.1, 1.3 invariants 1/2/3/7, 4.3, 5.4, 7.2]`, `docs/architecture.md`
  ("`pod_mavlink` owns … RX thread, governor hand-off, TX"),
  `docs/decisions/0021-pod-mavlink-slice-boundaries.md`
- **Supersedes:** nothing. Narrows one boundary stated in
  [0021](0021-pod-mavlink-slice-boundaries.md) point 3 (see below).

**Decision.** The running execution path that exercises the existing pure logic
against SITL is built as three new submodules **inside `pod_mavlink`**, plus a SITL
harness **inside `simulation/`**:

1. **`pod_mavlink/rx_runtime.py` — `MavlinkRxRuntime`.** One daemon thread; the
   **single writer** of `VehicleState` / `RCState` `[PRD 7.2]`. It reads through
   `MavlinkLink.recv()` (added this slice — routing the read through the one
   handle-owning object keeps invariant 7 literally true) and calls the existing
   pure `rx.py` builders. It holds **no safety policy**: it only turns messages into
   the two dataclasses the governor later reads. A read error is logged and the last
   good state is kept — loss of the link is not loss of the vehicle
   `[PRD 1.3 invariant 3]`. A malformed message is dropped; it never fabricates a
   "healthy" state. Before any message: the fail-safe initials from `rx.py`
   (`heartbeat_ok` already False, `kill_switch` True).

2. **`pod_mavlink/scheduler.py` — `FixedRateScheduler`.** A generic deadline-based
   fixed-rate driver at `COMMAND_RATE_HZ` = 20 `[PRD 1.1]`. Injected `now_ns` / `sleep`
   so timing is unit-testable with a fake clock. Drift-free (`start + n·period`), no
   busy-spin and no burst catch-up when a tick runs long (missed deadlines counted).
   A tick that raises stops the loop and propagates — the pod goes silent `[PRD 4.3]`
   and the FC's own GUIDED setpoint timeout takes over.

3. **`pod_mavlink/control_loop.py` — `ControlLoop.tick()`.** One governed cycle:
   `rx.snapshot()` → assemble `StateInput` → `pod_state.step()` → `pod_state.govern()`
   → `MavlinkLink.send()`. The governor is the **final authority** before transmission
   `[PRD 1.3 invariant 1]`; `send()` is the last gate and still transmits nothing for
   any non-SEND decision, never a zero-velocity substitute `[PRD 4.3]`. Returns a
   `CycleReport` (state, decision, reason, transmitted, heartbeat_ok, duration) which
   is the structured log line.

4. **`simulation/sitl/harness.py` — `SitlHarness`** (+ `run_sitl.md`). Wires the above
   to a MAVLink UDP endpoint. Everything SITL-specific is confined here: the
   connection string (a localhost placeholder from `sitl.yaml`, not a decision), and
   **obviously-synthetic** `SafetyEnvelope` / `MissionMode` / RC-channel numbers —
   the same "clearly-fake values to make the path runnable" pattern the unit tests
   already use. `src/pod_*` still may not import `simulation/` (enforced).

**Where the runtime lives, and why `pod_mavlink` and not a new package.**
`docs/architecture.md` already assigns "**RX thread, governor hand-off, TX**" to
`pod_mavlink`, and [0021](0021-pod-mavlink-slice-boundaries.md)'s "Trade-offs
accepted" already names "the RX thread itself, the 20 Hz scheduler that calls
`send()` on a cadence, and the M3 watchdog" as this module's deferred work. Putting
them here needs **no new top-level package, no new architecture rule, and no edit to
`tests/architecture/rules.py`** — `pod_mavlink`'s rule bans only GStreamer /
`pod_perception` / `pod_gcs` and sets no import allowlist, so importing `pod_state`,
`pod_config`, `threading` and `time` is already inside the stated boundary. A new
`pod_runtime` package would have been the larger architectural move.

**The one boundary this narrows.** [0021](0021-pod-mavlink-slice-boundaries.md)
point 3 said `pod_mavlink` does not import `pod_state`. That reasoning was specific to
`MavlinkLink.send()` — a plain TX method has no business calling `govern()`. It still
doesn't: `send()` is unchanged and imports nothing new. The **control loop** is a
different thing — an orchestrator whose whole job is to run `step()` then `govern()`
then `send()` — and it legitimately depends on both. `StateInput` / `StateOutput`
remain the hand-off contract; the loop builds and reads them, it does not reach into
`pod_state` internals.

**Reasoning.**
- `MavlinkLink.recv()` / `.flightmode` are thin pass-throughs: pymavlink resolves the
  autopilot-specific `custom_mode`→name mapping, so nothing here hard-codes
  ArduPilot's `GUIDED == 4`. `HEARTBEAT.base_mode`'s `SAFETY_ARMED` bit (`0x80`) is a
  MAVLink `common.xml` constant — implementing a spec, not inventing a number (same
  basis [0021] used for `MAV_FRAME_BODY_NED = 8`).
- `ControlLoop` takes `SafetyEnvelope` and `MissionMode` **already resolved**, exactly
  as [0019](0019-governor-takes-envelope-as-argument.md) /
  [0020](0020-state-machine-envelope-argument-and-scope.md) do for `govern()` /
  `step()`. It never reads `pod_config`, so a still-OPEN value surfaces as
  `ConfigOpenError` at the point of use, not as a guess in the loop.
- `target_system` / `target_component` have no default on `ControlLoop` either, for
  the same reason `send()` has none ([0021]): no document assigns MAVLink addressing.
- `MavlinkRxRuntime` refuses to decode `RC_CHANNELS` against an OPEN channel number
  (`ConfigOpenError`); `rc_channels=None` is a valid degraded mode that leaves RC at
  the fail-safe initial forever.

**No contract change.** `StateInput` / `StateOutput` / `VehicleState` / `RCState` /
`VelocityCommand` carry the whole flow unchanged. `PerceptionInputs` and `CycleReport`
are **runtime-internal** to `pod_mavlink`: built and consumed one call apart, never
serialised, never crossing a module boundary as a message — so they are deliberately
**not** in `pod_contracts.CROSS_MODULE_MESSAGES`. `PerceptionInputs` is the documented
seam where a future `pod_perception` + `pod_geometry` + `pod_guidance` chain will feed
the machine; until then the injected `command_source` returns an empty one and every
tick governs to SILENT.

**Lint config touched, not architecture.** `src/pod_mavlink/rx_runtime.py` is added to
the existing `ANN401` per-file-ignore list in `pyproject.toml`, alongside
`pod_contracts/codec.py` and the `pod_config` loaders — it decodes raw pymavlink
message objects, and `Any` is the honest annotation at that boundary, with the typed
contract (`VehicleState` / `RCState`) starting immediately after.

**Trade-offs accepted.**
- `import pod_mavlink` now transitively imports `pod_state`, `pod_config`, `threading`
  and `time`. `pod_mavlink` is no longer importable in total isolation from the pure
  control logic — acceptable, and consistent with `docs/architecture.md` already
  calling this module the "governor hand-off".
- The 20 Hz cadence is only *asserted* against a fake clock. Real jitter / the
  `SRx_*` congestion interaction (OD-07b) is an **M3 measurement**, unchanged by this
  slice — `[decision 0004]` "M3 debugging order: link first, perception second" still
  stands.
- No M3 control-thread **watchdog** yet ("a live process with a dead control thread is
  the dangerous case" `[PRD 5.5]`). A raising tick currently stops the scheduler and
  propagates; wrapping that in a supervisor that also confirms the pod fell silent is
  the next increment, in this same module.

**Alternatives considered.**
(a) **New `src/pod_runtime/` package** for the scheduler + control loop — rejected:
larger change (new package, new `tests/architecture/rules.py` entry, its own decision)
for orchestration the architecture doc already houses in `pod_mavlink`.
(b) **Put the control loop in `pod_state`** — rejected outright: `pod_state` is pure
(`tests/architecture/test_purity.py`); a thread driver and a `MavlinkLink` handle
cannot live there.
(c) **`command_source` imports `simulation` / a fixture directly from `pod_mavlink`** —
rejected: `src/pod_*` importing dev scaffolding is a boundary violation
(`tests/architecture/test_import_boundaries.py`). The source is *injected* from the
harness or the test instead.
(d) **Hard-code ArduPilot `GUIDED == 4` in the RX decode** — rejected: pymavlink
already resolves the mode string per autopilot; reading `link.flightmode` avoids a
firmware-specific magic number and keeps the PX4 swap a config change.

**Still open (unchanged by this slice).** OD-07b (`SRx_*` rate values), OD-12
(break-off radius from measured latency), OD-U6 (schedule), the RC channel map, the
mission latch, and the M3 watchdog. Nothing here closes any of them; the harness
supplies synthetic stand-ins only within `simulation/`.

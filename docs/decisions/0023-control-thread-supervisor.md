# 0023 — Control-thread supervisor: detect a dead/stalled control loop, stop the scheduler, report

- **Date:** 2026-09-07
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 5.5]` ("a live process with a dead control thread is the dangerous
  case"), `[PRD 4.3, 5.4]`, `docs/decisions/0022-mavlink-runtime-rx-scheduler-control-loop.md`
- **Supersedes:** nothing. Fills the "M3 watchdog" gap that
  [0022](0022-mavlink-runtime-rx-scheduler-control-loop.md) left named but unbuilt.

**Decision.** Add `pod_mavlink/supervisor.py` — `ControlSupervisor` — around the
existing `FixedRateScheduler` + `ControlLoop`. It owns the control thread and watches
**two independent failure signals**:

1. **Unexpected exit** — the control thread finished when the supervisor did not ask
   it to and no `max_ticks` bound was hit (a raising tick, or `scheduler.run()`
   returning early for any reason). Always active.
2. **No progress** — `FixedRateScheduler.tick_count` has not advanced for longer than
   a configured timeout. Active **only when a timeout is supplied**.

On **either** signal it does exactly two things: **stops the scheduler** and
**reports** (health enum + reason, a structured log line, an optional `on_failure`
callback). It does not touch `MavlinkLink`, does not construct a command, and does
not send zero velocity. Stopping the scheduler stops the ticks, which stops the
`MavlinkLink.send()` calls; there is no retransmit buffer anywhere in the runtime, so
"no stale command is resent" holds because *nothing ticks*, not because the
supervisor clears anything. The FC's own ~3 s GUIDED setpoint timeout then takes over
`[PRD 4.3, 5.4]` — the same dependency every other precondition failure already
relies on.

Health is one of: `STARTING`, `RUNNING`, `HEALTHY`, `STOPPED`, `FAILED`,
`WATCHDOG_TRIGGERED`. The first terminal state latched wins; `stop()` never
downgrades a `FAILED`/`WATCHDOG_TRIGGERED` to `STOPPED`, and a control-thread
exception observed during shutdown still resolves to `FAILED` — so the outcome is
deterministic regardless of thread ordering.

**Where the OPEN watchdog timeout is represented.**
`SafetyEnvelope.control_watchdog_timeout_ms` — a new boot-time-immutable safety field
(`pod_config`), shipped **OPEN** in `configs/airframes/_template.yaml`, registered as
**OD-A2** in `open_decisions.md`. It sits with `max_frame_age_ms` and
`breakoff_radius_m`: an M3-measured number the project does not have yet. Sizing it
needs the measured control-cycle distribution (how long a legitimately slow tick can
run) — guessing would either mask a real stall or trip on healthy jitter.

While OD-A2 is OPEN:
- `watchdog_timeout_ns_from_envelope(envelope)` returns `None`;
- `ControlSupervisor(..., watchdog_timeout_ns=None)` runs **unexpected-exit detection
  only**, and logs a `WARNING` at start saying the progress watchdog is disabled and
  why;
- `require_watchdog_timeout_ns(envelope)` is available for a caller that would rather
  refuse to start than run without the progress half — it raises `ConfigOpenError`.

The SITL harness supplies a **1 s** stand-in (`synthetic_watchdog_timeout_ns()`,
`simulation/sitl/harness.py`) purely so the stall path can be exercised. It is
commented, `simulation/`-only, and explicitly **not** the OD-A2 decision — the same
pattern the unit tests and `make_safety_envelope()` already use for OPEN numbers.

**Is `SafetyEnvelope` a contract change?** No. `SafetyEnvelope` lives in `pod_config`,
not `pod_contracts`; it is not in `pod_contracts.CROSS_MODULE_MESSAGES`, has no
`schemas/` JSON and no Kotlin mirror, and `CONTRACT_VERSION` is untouched. Adding a
field is a config-schema addition, and a boot-time-immutable safety timeout is
exactly what `SafetyEnvelope` is for `[PRD 7.2]`. `PodConfig.open_fields()` walks
dataclass fields generically, so it reports the new OPEN automatically. `ControlHealth`
/ `SupervisorReport` are runtime-internal observability (like `CycleReport`,
decision 0022), deliberately not registered.

**Threading.**
- MAVLink handle ownership is unchanged: `MavlinkLink` still the only holder; the
  supervisor never reads or writes it. Still exactly one writer to FC serial.
- Two threads: `pod-control` (runs `scheduler.run()`) and `pod-control-watchdog`
  (calls `poll_once()` on a timer). One `threading.Lock` guards all health/progress
  state; it is only ever held for field reads/writes, never across a `join()` or a
  user callback (`on_failure` fires outside the lock), so no lock-ordering deadlock is
  possible.
- `stop()` is idempotent and race-safe: it sets `_stop_requested` under the lock,
  stops the scheduler, sets the monitor-stop event, then joins both threads with a
  timeout. Concurrent `stop()` calls from many threads resolve to one clean shutdown.
- A tick that *hangs* (never returns) cannot be interrupted from Python; the
  supervisor still detects it (tick_count frozen → `WATCHDOG_TRIGGERED`), still calls
  `scheduler.stop()`, and `stop()` logs "did not exit … pod is silent, FC failsafe in
  effect" rather than blocking forever on the join.

**Timing / testability.** `now_ns` is injected everywhere; `poll_once()` is a single
health evaluation callable directly by tests with `run_monitor=False` for fully
deterministic assertions. The monitor thread's real-time poll interval is also
injected (`poll_interval_s`). No production timeout is hard-coded anywhere in `src/`.

**Trade-offs accepted.**
- On a real pod today the **progress watchdog does nothing** (OD-A2 OPEN). Only the
  unexpected-exit half is live. This is deliberate and logged; the alternative
  (guess a timeout) is the exact house-rule violation the project has paid for twice.
- The supervisor cannot kill a wedged tick — it can only stop scheduling further ones
  and report. Acceptable: a wedged tick is not issuing commands, and silence + FC
  failsafe is the designed safe state.
- `pod_mavlink` now also imports `threading` at module scope in one more file. No new
  cross-module edge (it already did, decision 0022).

**Alternatives considered.**
(a) **Supervisor sends a zero-velocity "safe" setpoint on failure** — rejected
outright: `[PRD 4.3]` "zero velocity is a command, and commanding a hover may be
exactly wrong." Going silent is the required behaviour, and there is no zero-velocity
path in the codebase by design.
(b) **Bake the watchdog timeout into `pod_mavlink` as a constant** — rejected: it is
an M3-measured safety number; a constant is a fabricated default. It belongs in the
per-airframe `SafetyEnvelope`, OPEN until measured.
(c) **Refuse to start the supervisor while the timeout is OPEN** — rejected as the
default: it would make the pod unrunnable for bring-up and SITL, and unexpected-exit
detection is real protection that does not need the number. Offered as an opt-in
(`require_watchdog_timeout_ns`) instead.
(d) **Watchdog re-checks governor preconditions itself** — rejected: that is a second
safety policy. A governed SILENT tick is healthy progress; the supervisor only asks
"is the loop alive and moving", never "should it have sent".
(e) **Separate `pod_watchdog` module** — rejected per decision 0022's reasoning: the
control runtime lives in `pod_mavlink`, and `[PRD 5.5]`'s watchdog is part of it.

**Still open.** **OD-A2** (`control_watchdog_timeout_ms`) — the no-progress timeout,
owner A, needs M3 measured control-cycle latency. Nothing else here closes any OPEN
decision. OD-07b (`SRx_*` rates), OD-12 (break-off radius), OD-U6 (schedule) unchanged.

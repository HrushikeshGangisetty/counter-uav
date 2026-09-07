# 0020 — `pod_state.machine.step()` takes `SafetyEnvelope` as an argument; BREAKOFF/ENGAGE stay guarded

- **Date:** 2026-09-07
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[ARCH State Machine]`, `docs/decisions/0019-governor-takes-envelope-as-argument.md`

**Decision.** `step(current: PodState, si: StateInput, envelope: SafetyEnvelope) ->
StateOutput`, matching `govern()`'s pattern from
[0019](0019-governor-takes-envelope-as-argument.md) and for the same reason:
`bbox_area_terminal` (LOCKED → TERMINAL) and `bbox_area_breakoff` (TERMINAL's exit)
are boot-loaded per-airframe config, not derivable from `StateInput`, and adding them
to that contract is a separate reviewed change this slice does not make.

IDLE, SEARCH, LOCKED, TERMINAL, LOST and ABORT are implemented. BREAKOFF and ENGAGE
raise `NotImplementedError` naming the blocking open decision (OD-U9, OD-U5) — both
as `current` states and as TERMINAL's exit toward them when `bbox_area_fraction`
crosses `bbox_area_breakoff`. A kill-switch-high check runs first and unconditionally,
before any per-state dispatch, so ABORT is reachable from every state including the
two still-guarded ones without touching their unimplemented logic.

**Reasoning.** `[ARCH State Machine]` states BREAKOFF's exit as "manoeuvre duration
expires" and ENGAGE's as "kinetic event handled by host drone" — neither is a
duration or boundary any project document states (OD-U9, OD-U5). Returning either
state without being able to also implement its exit would hand the FC advice this
module cannot itself unwind; raising is more honest than a state with no way out.

Two further reads worth recording, because they look like invented behaviour and
are not:
- LOCKED's "target lost > 1.5 s" exit reads `si.target_visible` as-is, with no
  internal timer. `pod_state` is pure and reads no clock, so the 1.5 s debounce must
  already be applied by whatever assembled `StateInput` before this module sees it;
  treating the existing boolean as the debounced signal is not a new condition.
- LOST's "5 s timeout → SEARCH" exit is **not implemented** for the same purity
  reason, and unlike the above there is no existing field to reinterpret: nothing in
  `StateInput` says how long the machine has been in LOST. Logged as **OD-U10**. Not
  a safety gap — LOST always emits SILENT, so staying there indefinitely commands
  nothing, exactly as the timeout path would once it reached SEARCH (also SILENT).

**Trade-offs accepted.** Same as 0019: one more parameter for the eventual M3 control
loop to wire up. Also: the machine can get "stuck" in LOST forever absent
reacquisition, until OD-U10 closes — acceptable because it is behaviourally
indistinguishable from the documented timeout path at the only level that matters
(no command is ever sent).

**Alternatives considered.**
(a) Thread envelope through `StateInput` — rejected per 0019's reasoning, unchanged.
(b) Invent a placeholder BREAKOFF/ENGAGE exit (e.g. a fixed duration) to keep the
table fully executable — rejected outright; the house rule is explicit that an
unmeasured, undocumented number must never become a plausible-looking default.
(c) Have LOST's timeout read `si.now_ns` against `previous_state`-implied entry time
by some other means — there is none available; `StateOutput.previous_state` records
only the immediately prior tick's state, not when LOST was entered relative to `now`.

**Still open.** OD-U9, OD-U5 (existing), and the new **OD-U10** (below).

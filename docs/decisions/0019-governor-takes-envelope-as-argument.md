# 0019 — `pod_state.govern()` takes `SafetyEnvelope` as a plain argument, not via `StateInput`

- **Date:** 2026-09-07
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 7.2]`, `docs/contracts.md`

**Decision.** `govern(candidate: StateOutput, si: StateInput, envelope: SafetyEnvelope) -> StateOutput`.
`SafetyEnvelope` (from `pod_config`) is passed as its own parameter. `StateInput`
(`pod_contracts.state`) is unchanged — no new field was added to it.

**Reasoning.** Implementing the governor's velocity/altitude/frame-staleness
preconditions requires the boot-loaded `SafetyEnvelope`, which `StateInput` does not
carry. `StateInput` is a registered cross-module message (`pod_contracts.registry`);
changing it is a contract change under `docs/contracts.md`'s own rule — update
`pod_contracts`, `schemas/`, `contracts.md` and the Kotlin mirror together, bump
`CONTRACT_VERSION`, get review from all three module owners. That's out of proportion
for what is, at bottom, wiring one module's own config into one of its own pure
functions. `pod_state`'s architecture rule (`tests/architecture/rules.py`) already
allowlists `pod_config` as an import, so this stays inside the existing boundary.

**Trade-offs accepted.** `govern()`'s call signature is no longer just "the two
things every StateOutput producer already has" — a caller must also thread the
per-airframe `SafetyEnvelope` through. That's one more thing for the eventual M3
control loop to wire up. Accepted because the alternative (folding config into a
contract dataclass) is a heavier, cross-team change for a need that is local to one
module.

**Alternatives considered.**
(a) Add `envelope: SafetyEnvelope` to `StateInput` — rejected per above; a real
contract change belongs in its own reviewed decision, not bundled into a governor
implementation slice.
(b) Have `govern()` call `pod_config.get_pod_config()` itself — rejected outright:
that's an I/O-adjacent global read inside a module `tests/architecture/test_purity.py`
requires to be pure (no globals, deterministic replay).

**Still open.** `pod_state.machine.step()` is unimplemented this session. Two of its
transitions need values no document states: the BREAKOFF manoeuvre duration, and
ENGAGE's exit condition ("kinetic event handled by host drone", OD-U5, boundary
undefined). Implementing `step()` honestly needs those closed first, or explicit
`OPEN`/`NotImplementedError` handling for exactly those two edges — a follow-on
slice, not folded in here.

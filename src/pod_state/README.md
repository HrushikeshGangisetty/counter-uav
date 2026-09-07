# pod_state

**Owner:** Person A (Hrushikesh) · **Must never import:** GStreamer, pymavlink
`[PRD 2.3]` · **PURE** — `now_ns` is an argument, never a clock read.

The eight-state machine (`machine.py`, table transcribed verbatim from
`[ARCH State Machine]`) plus envelope clamps, rate limits and the **safety governor**
(`governor.py`).

```
IDLE → SEARCH → LOCKED → TERMINAL → BREAKOFF (surveillance) | ENGAGE (intercept)
                   ↓                              ABORT ← kill switch, from any state
                 LOST → SEARCH (5 s)
```

## The one rule that matters `[PRD 4.3]`

> *"On any precondition failure the governor must stop sending setpoints, **not send
> zero velocity**. Zero velocity is a command, and commanding a hover may be exactly
> wrong. Going silent lets ArduPilot's own tested failsafe take over after its
> setpoint timeout."*

`CommandDecision.SILENT` always carries `command=None`. **There is no zero-velocity
code path in this module and none may be added.**

`GOVERNOR_PRECONDITIONS` holds each check with its source citation, so
`tests/unit/test_spec_governor.py` can assert none has been quietly dropped.

**Status:** `govern()` is implemented — [decision 0019](../../docs/decisions/0019-governor-takes-envelope-as-argument.md)
threads the boot-loaded `SafetyEnvelope` in as its own argument rather than through
`StateInput`. `step()` is implemented for IDLE, SEARCH, LOCKED, TERMINAL, LOST and
ABORT — [decision 0020](../../docs/decisions/0020-state-machine-envelope-argument-and-scope.md).
BREAKOFF and ENGAGE (as `current` states, and as TERMINAL's exit toward them) raise
`NotImplementedError` naming **OD-U9** (BREAKOFF manoeuvre duration) or **OD-U5**
(ENGAGE's kinetic-event boundary) — both undocumented. LOST's 5 s timeout to SEARCH
is also unimplemented (**OD-U10**): `step()` is pure and has no elapsed-time-in-LOST
signal to compute it from; not a safety gap, since LOST always emits SILENT.

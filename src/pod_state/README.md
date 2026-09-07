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

**Status:** table and precondition list are data now; `step()` and `govern()` are M2.
The executable acceptance criteria already exist as strict-xfail specs.

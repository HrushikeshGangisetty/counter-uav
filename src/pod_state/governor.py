"""The safety governor. PURE --- no I/O, no threads, no globals.

THE ONE RULE THAT MATTERS [PRD 4.3]:
    "on any precondition failure the governor must stop sending setpoints, not send
    zero velocity. Zero velocity is a command, and commanding a hover may be exactly
    wrong. Going silent lets ArduPilot's own tested failsafe take over after its
    setpoint timeout" --- roughly 3 seconds [PRD 5.4].

There is deliberately no zero-velocity code path in this module.
"""

from __future__ import annotations

from pod_contracts import CommandDecision, StateInput, StateOutput

#: The preconditions the governor checks, each traced to its source. Held as data so
#: tests/unit/spec_governor.py can assert the implementation covers all of them and
#: none has been quietly dropped.
GOVERNOR_PRECONDITIONS: tuple[tuple[str, str], ...] = (
    ("fc_mode_is_guided", "PRD 1.3 invariant 2 --- honoured only in GUIDED mode"),
    (
        "heartbeat_within_500ms",
        "PRD 1.3 invariant 3 --- heartbeat gap beyond 500 ms is loss of pod",
    ),
    (
        "kill_switch_low",
        "ARCH State Machine --- kill switch high -> ABORT, pod stops MAVLink writes",
    ),
    ("ai_enable_high", "PRD 1.3 invariant 4 --- AI-enable RC channel high"),
    ("lock_trigger_asserted", "PRD 1.3 invariant 4 --- target-lock RC channel triggered"),
    ("frame_not_stale", "PRD 2.3 --- consumers independently reject stale data"),
    ("within_velocity_envelope", "PRD 7.2 --- envelope clamps, boot-time immutable config"),
    ("within_altitude_envelope", "PRD 4.6 --- geofence and altitude envelope enforcement"),
)


def govern(candidate: StateOutput, si: StateInput) -> StateOutput:
    """Apply the safety governor to a state-machine output. PURE.

    ⚠ NOT IMPLEMENTED --- M2, Person A.

    Contract when implemented:
      * if every precondition in GOVERNOR_PRECONDITIONS holds, return the candidate
        (with envelope clamps and rate limits applied);
      * otherwise return decision=SILENT and command=None, with ``reason`` naming the
        precondition that failed. Never a zero-velocity command;
      * pure: takes ``si.now_ns``, reads no clock, holds no state between calls.
    """
    raise NotImplementedError("pod_state.govern: M2 / Person A")


def silent(reason: str, candidate: StateOutput) -> StateOutput:
    """Build the SILENT output. The only sanctioned way to refuse to command."""
    return StateOutput(
        state=candidate.state,
        decision=CommandDecision.SILENT,
        command=None,
        reason=reason,
        previous_state=candidate.previous_state,
    )

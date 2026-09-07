"""The safety governor. PURE --- no I/O, no threads, no globals.

THE ONE RULE THAT MATTERS [PRD 4.3]:
    "on any precondition failure the governor must stop sending setpoints, not send
    zero velocity. Zero velocity is a command, and commanding a hover may be exactly
    wrong. Going silent lets ArduPilot's own tested failsafe take over after its
    setpoint timeout" --- roughly 3 seconds [PRD 5.4].

There is deliberately no zero-velocity code path in this module.
"""

from __future__ import annotations

from pod_config import SafetyEnvelope
from pod_contracts import CommandDecision, FlightMode, StateInput, StateOutput

from ._envelope import require as _require

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


def govern(candidate: StateOutput, si: StateInput, envelope: SafetyEnvelope) -> StateOutput:
    """Apply the safety governor to a state-machine output. PURE.

    ``envelope`` is the boot-loaded, per-airframe SafetyEnvelope [PRD 1.3 invariant 6].
    It is not part of StateInput: StateInput is a cross-module contract
    (pod_contracts.state) and threading config through it is a contract change
    requiring its own decision entry, not something to do inside this slice.
    Passing it as a plain argument keeps govern() callable with whatever the boot-time
    config actually resolved to, while staying pure --- no clock read, no I/O.

    Every check below is traced to GOVERNOR_PRECONDITIONS; the order matches the
    tuple. If a required config value is itself OPEN (e.g. max_frame_age_ms,
    OD-12/OD-07b-adjacent gaps), this raises ConfigOpenError rather than silently
    treating the check as passed or failed --- an unmade decision must fail loudly at
    the point of use [pod_config.errors.ConfigOpenError].

    Contract:
      * if every precondition holds, return the candidate unchanged (rate limits and
        further envelope clamping beyond the pass/fail checks below are a later M2
        increment, not invented here);
      * otherwise return decision=SILENT and command=None, with ``reason`` naming the
        precondition that failed. Never a zero-velocity command;
      * pure: takes ``si.now_ns``, reads no clock, holds no state between calls.
    """
    if si.rc.kill_switch:
        return silent("kill_switch_low", candidate)

    if si.vehicle.mode is not FlightMode.GUIDED:
        return silent("fc_mode_is_guided", candidate)

    if not si.vehicle.heartbeat_ok(si.now_ns):
        return silent("heartbeat_within_500ms", candidate)

    if not si.rc.ai_enable:
        return silent("ai_enable_high", candidate)

    if not si.rc.lock_trigger:
        return silent("lock_trigger_asserted", candidate)

    if si.frame is not None:
        max_age_ns = _require(envelope.max_frame_age_ms, "max_frame_age_ms") * 1_000_000
        if si.frame.age_ns(si.now_ns) > max_age_ns:
            return silent("frame_not_stale", candidate)

    if candidate.command is not None:
        max_speed_ms = _require(envelope.max_pursuit_speed_ms, "max_pursuit_speed_ms")
        speed_ms = (
            candidate.command.vx_ms**2 + candidate.command.vy_ms**2 + candidate.command.vz_ms**2
        ) ** 0.5
        if speed_ms > max_speed_ms:
            return silent("within_velocity_envelope", candidate)

        max_altitude_m = _require(envelope.max_altitude_m, "max_altitude_m")
        altitude_m = -si.vehicle.pos_down_m
        if altitude_m > max_altitude_m:
            return silent("within_altitude_envelope", candidate)

    return candidate


def silent(reason: str, candidate: StateOutput) -> StateOutput:
    """Build the SILENT output. The only sanctioned way to refuse to command."""
    return StateOutput(
        state=candidate.state,
        decision=CommandDecision.SILENT,
        command=None,
        reason=reason,
        previous_state=candidate.previous_state,
    )

"""Executable specification for the safety governor.

govern() is implemented as of this slice.

Note on max_frame_age_ms: it is OPEN in the shipped config (no document states a
staleness threshold). That means govern() cannot honestly decide "is this frame
stale" against real boot-time config today, and raises ConfigOpenError rather than
guessing --- see test_open_frame_age_threshold_raises_rather_than_guessing. Every
other test below supplies an explicit, obviously-synthetic max_frame_age_ms via
make_safety_envelope() so it can exercise the rest of the governor independently of
that still-open decision.
"""

from __future__ import annotations

import pytest

from pod_config import ConfigOpenError
from pod_contracts import CommandDecision, FlightMode, PodState, StateOutput
from pod_state import GOVERNOR_PRECONDITIONS, govern
from simulation.mocks import (
    make_rc_state,
    make_safety_envelope,
    make_state_input,
    make_vehicle_state,
    make_velocity_command,
)

#: Synthetic, obviously-not-measured: only used to unblock tests that are not
#: exercising the frame-staleness precondition itself.
_TEST_MAX_FRAME_AGE_MS = 1_000_000.0


def _envelope(**overrides):
    overrides.setdefault("max_frame_age_ms", _TEST_MAX_FRAME_AGE_MS)
    return make_safety_envelope(**overrides)


def _candidate() -> StateOutput:
    return StateOutput(
        state=PodState.LOCKED,
        decision=CommandDecision.SEND,
        command=make_velocity_command(),
        reason="pursuing",
    )


def test_every_documented_precondition_is_declared() -> None:
    """This one runs today: the precondition list must stay complete and cited."""
    names = {n for n, _ in GOVERNOR_PRECONDITIONS}
    assert {"fc_mode_is_guided", "heartbeat_within_500ms", "kill_switch_low"} <= names
    assert all(citation for _, citation in GOVERNOR_PRECONDITIONS), "every ban needs a source"


def test_non_guided_mode_goes_silent() -> None:
    """[PRD 1.3 invariant 2] pod commands are honoured only in GUIDED mode."""
    si = make_state_input(vehicle=make_vehicle_state(mode=FlightMode.OTHER))
    out = govern(_candidate(), si, _envelope())
    assert out.decision is CommandDecision.SILENT
    assert out.command is None


def test_heartbeat_gap_beyond_500ms_goes_silent() -> None:
    """[PRD 1.3 invariant 3]."""
    si = make_state_input(vehicle=make_vehicle_state(heartbeat_age_ns=600_000_000))
    out = govern(_candidate(), si, _envelope())
    assert out.decision is CommandDecision.SILENT


def test_kill_switch_goes_silent() -> None:
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    assert govern(_candidate(), si, _envelope()).decision is CommandDecision.SILENT


def test_ai_enable_alone_is_not_sufficient() -> None:
    """[PRD 1.3 invariant 4] engagement needs AI-enable AND target-lock."""
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=False))
    assert govern(_candidate(), si, _envelope()).decision is CommandDecision.SILENT


def test_silent_never_means_zero_velocity() -> None:
    """[PRD 4.3] "Zero velocity is a command, and commanding a hover may be exactly
    wrong." A SILENT output carries no command at all."""
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    out = govern(_candidate(), si, _envelope())
    assert out.command is None


def test_governor_is_pure() -> None:
    si = make_state_input()
    envelope = _envelope()
    assert govern(_candidate(), si, envelope) == govern(_candidate(), si, envelope)


def test_every_precondition_passing_returns_the_candidate_unchanged() -> None:
    si = make_state_input()
    candidate = _candidate()
    assert govern(candidate, si, _envelope()) == candidate


def test_velocity_over_envelope_goes_silent() -> None:
    """[PRD 7.2] envelope clamps, boot-time immutable config."""
    si = make_state_input()
    base = make_velocity_command()
    fast_candidate = StateOutput(
        state=PodState.LOCKED,
        decision=CommandDecision.SEND,
        command=type(base)(frame=base.frame, vx_ms=999.0, vy_ms=0.0, vz_ms=0.0, yaw_rate_rads=0.0),
        reason="pursuing",
    )
    out = govern(fast_candidate, si, _envelope())
    assert out.decision is CommandDecision.SILENT
    assert out.reason == "within_velocity_envelope"
    assert out.command is None


def test_altitude_over_envelope_goes_silent() -> None:
    """[PRD 4.6] geofence and altitude envelope enforcement. pos_down_m is NED, so an
    altitude above the 100 m envelope is a large negative pos_down_m."""
    si = make_state_input(vehicle=make_vehicle_state(pos_down_m=-999.0))
    out = govern(_candidate(), si, _envelope())
    assert out.decision is CommandDecision.SILENT
    assert out.reason == "within_altitude_envelope"


def test_no_frame_skips_the_staleness_check() -> None:
    """StateInput.frame is Optional precisely because the machine must still tick
    with no frame; the governor must not fail closed on a missing frame the same way
    it would on a stale one."""
    si = make_state_input(frame=None)
    out = govern(_candidate(), si, _envelope())
    assert out.decision is CommandDecision.SEND


def test_open_frame_age_threshold_raises_rather_than_guessing() -> None:
    """[house rule] a value not stated in any document is OPEN; reading it at the
    point of use raises ConfigOpenError rather than becoming a plausible default."""
    si = make_state_input()
    assert si.frame is not None
    with pytest.raises(ConfigOpenError):
        govern(_candidate(), si, make_safety_envelope())  # max_frame_age_ms left OPEN

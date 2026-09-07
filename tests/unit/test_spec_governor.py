"""Executable specification for the safety governor.

These tests are marked xfail(strict=True) because pod_state.govern is M2 work. They
are not placeholders: they are the acceptance criteria, written down before the
implementation, and each one flips to a passing test the moment the behaviour lands.
An XPASS is a hard failure, so the ledger cannot silently rot.
"""

from __future__ import annotations

import pytest

from pod_contracts import CommandDecision, FlightMode, PodState, StateOutput
from pod_state import GOVERNOR_PRECONDITIONS, govern
from simulation.mocks import (
    make_rc_state,
    make_state_input,
    make_vehicle_state,
    make_velocity_command,
)

M2 = pytest.mark.xfail(strict=True, reason="pod_state.govern is M2 / Person A")


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


@M2
def test_non_guided_mode_goes_silent() -> None:
    """[PRD 1.3 invariant 2] pod commands are honoured only in GUIDED mode."""
    si = make_state_input(vehicle=make_vehicle_state(mode=FlightMode.OTHER))
    out = govern(_candidate(), si)
    assert out.decision is CommandDecision.SILENT
    assert out.command is None


@M2
def test_heartbeat_gap_beyond_500ms_goes_silent() -> None:
    """[PRD 1.3 invariant 3]."""
    si = make_state_input(vehicle=make_vehicle_state(heartbeat_age_ns=600_000_000))
    out = govern(_candidate(), si)
    assert out.decision is CommandDecision.SILENT


@M2
def test_kill_switch_goes_silent() -> None:
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    assert govern(_candidate(), si).decision is CommandDecision.SILENT


@M2
def test_ai_enable_alone_is_not_sufficient() -> None:
    """[PRD 1.3 invariant 4] engagement needs AI-enable AND target-lock."""
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=False))
    assert govern(_candidate(), si).decision is CommandDecision.SILENT


@M2
def test_silent_never_means_zero_velocity() -> None:
    """[PRD 4.3] "Zero velocity is a command, and commanding a hover may be exactly
    wrong." A SILENT output carries no command at all."""
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    out = govern(_candidate(), si)
    assert out.command is None


@M2
def test_governor_is_pure() -> None:
    si = make_state_input()
    assert govern(_candidate(), si) == govern(_candidate(), si)

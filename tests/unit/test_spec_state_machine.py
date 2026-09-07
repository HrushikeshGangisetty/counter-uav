"""Executable specification for the state machine.

Implemented this slice: IDLE, SEARCH, LOCKED, TERMINAL, LOST, ABORT. BREAKOFF and
ENGAGE stay xfail(strict=True): they raise NotImplementedError naming the open
decision that blocks each (OD-U9, OD-U5), so any test exercising them still fails
today, as intended. test_surveillance_never_reaches_engage stays xfail for the same
reason --- it iterates every PodState, including the two still-guarded ones.
"""

from __future__ import annotations

import pytest

from pod_config import ConfigOpenError
from pod_contracts import CommandDecision, MissionMode, PodState
from pod_state import step
from simulation.mocks import make_rc_state, make_safety_envelope, make_state_input

M2 = pytest.mark.xfail(strict=True, reason="pod_state.step BREAKOFF/ENGAGE: OD-U9 / OD-U5")

#: bbox thresholds are OPEN in the shipped config; tests that need to get past LOCKED
#: or TERMINAL supply obviously-synthetic values here, the same way
#: test_spec_governor.py supplies a synthetic max_frame_age_ms.
_ENVELOPE = make_safety_envelope(bbox_area_terminal=0.3, bbox_area_breakoff=0.45)


def test_idle_requires_ai_enable_to_reach_search() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=False, lock_trigger=False))
    assert step(PodState.IDLE, si, _ENVELOPE).state is PodState.IDLE


def test_idle_reaches_search_when_ai_enable_is_high() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=False))
    out = step(PodState.IDLE, si, _ENVELOPE)
    assert out.state is PodState.SEARCH
    assert out.decision is CommandDecision.SILENT


def test_kill_switch_from_any_state_reaches_abort() -> None:
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    for state in PodState:
        assert step(state, si, _ENVELOPE).state is PodState.ABORT


def test_abort_emits_silent() -> None:
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    assert step(PodState.LOCKED, si, _ENVELOPE).decision is CommandDecision.SILENT


def test_abort_returns_to_idle_once_kill_switch_is_low() -> None:
    si = make_state_input(rc=make_rc_state(kill_switch=False))
    out = step(PodState.ABORT, si, _ENVELOPE)
    assert out.state is PodState.IDLE
    assert out.decision is CommandDecision.SILENT


def test_step_is_deterministic() -> None:
    si = make_state_input()
    assert step(PodState.SEARCH, si, _ENVELOPE) == step(PodState.SEARCH, si, _ENVELOPE)


@M2
def test_surveillance_never_reaches_engage() -> None:
    """[PRD 1.2] surveillance mode engages under no circumstances."""
    si = make_state_input(mission_mode=MissionMode.SURVEILLANCE, bbox_area_fraction=0.9)
    for state in PodState:
        assert step(state, si, _ENVELOPE).state is not PodState.ENGAGE


def test_search_reaches_locked_on_lock_and_visible_target() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=True), target_visible=True)
    out = step(PodState.SEARCH, si, _ENVELOPE)
    assert out.state is PodState.LOCKED


def test_search_stays_in_search_without_a_visible_target() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=True), target_visible=False)
    assert step(PodState.SEARCH, si, _ENVELOPE).state is PodState.SEARCH


def test_locked_sends_the_proposed_command_while_pursuing() -> None:
    si = make_state_input(bbox_area_fraction=0.01)  # well under the terminal threshold
    out = step(PodState.LOCKED, si, _ENVELOPE)
    assert out.state is PodState.LOCKED
    assert out.decision is CommandDecision.SEND
    assert out.command == si.proposed_command


def test_locked_crosses_into_terminal_at_the_bbox_threshold() -> None:
    si = make_state_input(bbox_area_fraction=0.5)
    out = step(PodState.LOCKED, si, _ENVELOPE)
    assert out.state is PodState.TERMINAL


def test_locked_exits_to_lost_when_target_not_visible() -> None:
    si = make_state_input(target_visible=False)
    out = step(PodState.LOCKED, si, _ENVELOPE)
    assert out.state is PodState.LOST
    assert out.decision is CommandDecision.SILENT
    assert out.command is None


def test_locked_exits_to_search_on_pilot_unlock() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=False))
    out = step(PodState.LOCKED, si, _ENVELOPE)
    assert out.state is PodState.SEARCH


def test_locked_with_open_bbox_terminal_threshold_raises() -> None:
    """[house rule] bbox_area_terminal is OPEN in the shipped config; the machine
    must refuse to guess rather than silently pick a plausible-looking number."""
    si = make_state_input()
    with pytest.raises(ConfigOpenError):
        step(PodState.LOCKED, si, make_safety_envelope())  # bbox_area_terminal OPEN


def test_terminal_exits_to_lost_when_target_not_visible() -> None:
    si = make_state_input(target_visible=False)
    out = step(PodState.TERMINAL, si, _ENVELOPE)
    assert out.state is PodState.LOST


def test_terminal_keeps_sending_while_under_the_breakoff_threshold() -> None:
    si = make_state_input(bbox_area_fraction=0.35)
    out = step(PodState.TERMINAL, si, _ENVELOPE)
    assert out.state is PodState.TERMINAL
    assert out.decision is CommandDecision.SEND


@M2
def test_terminal_over_breakoff_in_surveillance_is_guarded_by_od_u9() -> None:
    si = make_state_input(mission_mode=MissionMode.SURVEILLANCE, bbox_area_fraction=0.9)
    step(PodState.TERMINAL, si, _ENVELOPE)


@M2
def test_terminal_over_breakoff_in_intercept_is_guarded_by_od_u5() -> None:
    si = make_state_input(mission_mode=MissionMode.INTERCEPT, bbox_area_fraction=0.9)
    step(PodState.TERMINAL, si, _ENVELOPE)


def test_lost_reacquires_to_locked() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=True), target_visible=True)
    out = step(PodState.LOST, si, _ENVELOPE)
    assert out.state is PodState.LOCKED


def test_lost_stays_lost_and_silent_without_reacquisition() -> None:
    """The 5 s timeout to SEARCH [ARCH State Machine] is not implemented (OD-U10:
    step() is pure and has no elapsed-time-in-LOST signal to compute it from).
    Staying in LOST is safe: both paths emit SILENT."""
    si = make_state_input(target_visible=False)
    out = step(PodState.LOST, si, _ENVELOPE)
    assert out.state is PodState.LOST
    assert out.decision is CommandDecision.SILENT
    assert out.command is None


@M2
def test_breakoff_is_not_yet_implemented() -> None:
    si = make_state_input()
    step(PodState.BREAKOFF, si, _ENVELOPE)


@M2
def test_engage_is_not_yet_implemented() -> None:
    si = make_state_input()
    step(PodState.ENGAGE, si, _ENVELOPE)

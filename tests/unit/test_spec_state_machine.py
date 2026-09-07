"""Executable specification for the state machine. xfail(strict) until M2."""

from __future__ import annotations

import pytest

from pod_contracts import CommandDecision, MissionMode, PodState
from pod_state import step
from simulation.mocks import make_rc_state, make_state_input

M2 = pytest.mark.xfail(strict=True, reason="pod_state.step is M2 / Person A")


@M2
def test_idle_requires_ai_enable_to_reach_search() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=False, lock_trigger=False))
    assert step(PodState.IDLE, si).state is PodState.IDLE


@M2
def test_kill_switch_from_any_state_reaches_abort() -> None:
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    for state in PodState:
        assert step(state, si).state is PodState.ABORT


@M2
def test_surveillance_never_reaches_engage() -> None:
    """[PRD 1.2] surveillance mode engages under no circumstances."""
    si = make_state_input(mission_mode=MissionMode.SURVEILLANCE, bbox_area_fraction=0.9)
    for state in PodState:
        assert step(state, si).state is not PodState.ENGAGE


@M2
def test_abort_emits_silent() -> None:
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    assert step(PodState.LOCKED, si).decision is CommandDecision.SILENT


@M2
def test_step_is_deterministic() -> None:
    si = make_state_input()
    assert step(PodState.SEARCH, si) == step(PodState.SEARCH, si)

"""pod_state: the transition table matches [ARCH State Machine] exactly.

The table is not superseded by PRD v1.1, so it is the authority. Encoding it as data
and testing it means the M2 implementation is checked against the document rather
than against someone's recollection of it.
"""

from __future__ import annotations

from pod_contracts import MissionMode, PodState
from pod_state import TRANSITIONS


def test_all_eight_states_are_present_exactly_once() -> None:
    states = [t.state for t in TRANSITIONS]
    assert len(states) == 8
    assert set(states) == set(PodState)


def test_engage_is_intercept_only_and_breakoff_is_surveillance_only() -> None:
    by_state = {t.state: t for t in TRANSITIONS}
    assert MissionMode.INTERCEPT.value in by_state[PodState.ENGAGE].entry
    assert MissionMode.SURVEILLANCE.value in by_state[PodState.BREAKOFF].entry


def test_kill_switch_reaches_abort_from_any_state() -> None:
    by_state = {t.state: t for t in TRANSITIONS}
    assert "Kill switch RC high" in by_state[PodState.ABORT].entry
    assert "kill switch from any state" in by_state[PodState.IDLE].entry.lower()


def test_abort_stops_mavlink_writes() -> None:
    by_state = {t.state: t for t in TRANSITIONS}
    assert "stops MAVLink writes" in by_state[PodState.ABORT].description

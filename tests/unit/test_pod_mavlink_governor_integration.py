"""pod_state.govern() -> pod_mavlink.MavlinkLink.send(): the hand-off StateOutput
is meant for [docs/contracts.md registry]. pod_mavlink does not import pod_state
(the two only meet through the StateOutput contract), so this integration is
verified here, at the boundary, rather than by a call inside either module.
"""

from __future__ import annotations

from pod_config import SafetyEnvelope
from pod_contracts import CommandDecision, PodState, StateOutput
from pod_mavlink import MavlinkLink
from pod_state import govern
from simulation.mocks import (
    make_rc_state,
    make_safety_envelope,
    make_state_input,
    make_velocity_command,
)


class _FakeMav:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    def set_position_target_local_ned_send(self, **fields: object) -> None:
        self.sent.append(fields)


class _FakeConn:
    def __init__(self) -> None:
        self.mav = _FakeMav()

    def close(self) -> None:
        pass


def _candidate() -> StateOutput:
    return StateOutput(
        state=PodState.LOCKED,
        decision=CommandDecision.SEND,
        command=make_velocity_command(),
        reason="pursuing",
    )


def _envelope() -> SafetyEnvelope:
    return make_safety_envelope(max_frame_age_ms=1_000_000.0)


def test_governed_silent_reaches_pod_mavlink_as_no_transmission() -> None:
    """[PRD 1.3 invariant 4] AI-enable alone is not sufficient -> governor SILENT
    -> MavlinkLink.send() transmits nothing."""
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=False))
    governed = govern(_candidate(), si, _envelope())
    assert governed.decision is CommandDecision.SILENT

    link = MavlinkLink(device="udp:127.0.0.1:14550")
    link._conn = _FakeConn()
    sent = link.send(governed, time_boot_ms=0, target_system=1, target_component=1)

    assert sent is False
    assert link._conn.mav.sent == []


def test_governed_send_reaches_pod_mavlink_as_one_transmission() -> None:
    si = make_state_input(rc=make_rc_state(ai_enable=True, lock_trigger=True))
    candidate = _candidate()
    governed = govern(candidate, si, _envelope())
    assert governed.decision is CommandDecision.SEND

    link = MavlinkLink(device="udp:127.0.0.1:14550")
    link._conn = _FakeConn()
    sent = link.send(governed, time_boot_ms=0, target_system=1, target_component=1)

    assert sent is True
    assert len(link._conn.mav.sent) == 1
    assert candidate.command is not None
    assert link._conn.mav.sent[0]["vx"] == candidate.command.vx_ms


def test_kill_switch_reaches_pod_mavlink_as_no_transmission() -> None:
    """[PRD 1.3 invariant 2, 3] every governor precondition failure ends the same
    way at the MAVLink boundary: silence, never a substituted command."""
    si = make_state_input(rc=make_rc_state(kill_switch=True))
    governed = govern(_candidate(), si, _envelope())
    assert governed.decision is CommandDecision.SILENT
    assert governed.command is None

    link = MavlinkLink(device="udp:127.0.0.1:14550")
    link._conn = _FakeConn()
    sent = link.send(governed, time_boot_ms=0, target_system=1, target_component=1)

    assert sent is False

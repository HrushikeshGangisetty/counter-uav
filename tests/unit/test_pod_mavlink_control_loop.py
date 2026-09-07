"""pod_mavlink.control_loop.ControlLoop: rx -> pod_state -> MavlinkLink.send().

The end-to-end runtime path, with the RX thread and the socket faked out:

* a fake rx exposing ``snapshot()`` -> (VehicleState, RCState);
* a real ``MavlinkLink`` with an injected fake ``_conn`` (same trick as
  test_pod_mavlink_link.py), so the real SEND/SILENT gate is exercised;
* an injected ``command_source`` standing in for perception/guidance.

The governor stays the final authority [PRD 1.3 invariant 1]: every precondition
failure ends as no transmission, never a substituted command.
"""

from __future__ import annotations

from pod_contracts import CommandDecision, FlightMode, MissionMode, PodState
from pod_mavlink import ControlLoop, MavlinkLink, PerceptionInputs
from simulation.mocks import (
    make_rc_state,
    make_safety_envelope,
    make_vehicle_state,
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


class _FakeRx:
    def __init__(self, vehicle, rc) -> None:
        self._vehicle = vehicle
        self._rc = rc

    def snapshot(self):
        return self._vehicle, self._rc


def _envelope():
    return make_safety_envelope(
        bbox_area_terminal=0.30, bbox_area_breakoff=0.45, max_frame_age_ms=250.0
    )


def _loop(*, vehicle=None, rc=None, command_source=None, state=PodState.LOCKED):
    link = MavlinkLink(device="udp:127.0.0.1:14550")
    conn = _FakeConn()
    link._conn = conn
    rx = _FakeRx(
        vehicle if vehicle is not None else make_vehicle_state(mode=FlightMode.GUIDED),
        rc
        if rc is not None
        else make_rc_state(ai_enable=True, lock_trigger=True, kill_switch=False),
    )
    loop = ControlLoop(
        link=link,
        rx=rx,
        envelope=_envelope(),
        mission_mode=MissionMode.SURVEILLANCE,
        target_system=1,
        target_component=1,
        command_source=command_source if command_source is not None else _visible_target,
        state=state,
        now_ns=lambda: 0,
    )
    return loop, conn


def _visible_target(_now_ns: int) -> PerceptionInputs:
    return PerceptionInputs(
        frame=None,
        proposed_command=make_velocity_command(),
        target_visible=True,
        bbox_area_fraction=0.01,
        locked_track_id=1,
    )


def _no_target(_now_ns: int) -> PerceptionInputs:
    return PerceptionInputs()


def test_send_decision_results_in_one_transmission() -> None:
    loop, conn = _loop()
    report = loop.tick(now_ns=1_000_000)
    assert report.decision is CommandDecision.SEND
    assert report.transmitted is True
    assert len(conn.mav.sent) == 1
    assert conn.mav.sent[0]["vx"] == make_velocity_command().vx_ms


def test_silent_decision_results_in_no_transmission() -> None:
    """No visible target: LOCKED -> LOST, SILENT, nothing sent."""
    loop, conn = _loop(command_source=_no_target)
    report = loop.tick(now_ns=1_000_000)
    assert report.state is PodState.LOST
    assert report.decision is CommandDecision.SILENT
    assert report.transmitted is False
    assert conn.mav.sent == []


def test_kill_switch_prevents_transmission() -> None:
    loop, conn = _loop(rc=make_rc_state(kill_switch=True))
    report = loop.tick(now_ns=1_000_000)
    assert report.state is PodState.ABORT
    assert report.transmitted is False
    assert conn.mav.sent == []


def test_heartbeat_loss_prevents_transmission() -> None:
    """step() would propose SEND; the governor vetoes on the 500 ms heartbeat gap."""
    loop, conn = _loop(
        vehicle=make_vehicle_state(mode=FlightMode.GUIDED, heartbeat_age_ns=600_000_000)
    )
    report = loop.tick(now_ns=1_000_000)
    assert report.decision is CommandDecision.SILENT
    assert report.reason == "heartbeat_within_500ms"
    assert report.transmitted is False
    assert report.heartbeat_ok is False
    assert conn.mav.sent == []


def test_non_guided_mode_prevents_transmission() -> None:
    loop, conn = _loop(vehicle=make_vehicle_state(mode=FlightMode.OTHER))
    report = loop.tick(now_ns=1_000_000)
    assert report.decision is CommandDecision.SILENT
    assert report.reason == "fc_mode_is_guided"
    assert conn.mav.sent == []


def test_governor_is_the_final_authority_even_when_the_machine_says_send() -> None:
    """ai_enable without lock_trigger [PRD 1.3 invariant 4]: machine may still be in
    LOCKED, but govern() refuses."""
    loop, conn = _loop(rc=make_rc_state(ai_enable=True, lock_trigger=False))
    report = loop.tick(now_ns=1_000_000)
    assert report.decision is CommandDecision.SILENT
    assert report.transmitted is False
    assert conn.mav.sent == []


def test_tick_advances_the_state_machine_and_tick_index() -> None:
    loop, _conn = _loop(
        state=PodState.IDLE,
        rc=make_rc_state(ai_enable=True, lock_trigger=True, kill_switch=False),
        command_source=_visible_target,
    )
    r0 = loop.tick(now_ns=0)
    assert r0.state is PodState.SEARCH  # IDLE -> SEARCH on ai_enable
    assert r0.tick_index == 0
    r1 = loop.tick(now_ns=50_000_000)
    assert r1.state is PodState.LOCKED  # SEARCH -> LOCKED on lock + visible
    assert r1.tick_index == 1
    r2 = loop.tick(now_ns=100_000_000)
    assert r2.state is PodState.LOCKED
    assert r2.decision is CommandDecision.SEND


def test_cycle_report_carries_timing_and_log_fields() -> None:
    loop, _conn = _loop()
    report = loop.tick(now_ns=1_000_000)
    assert report.duration_ns >= 0
    fields = report.as_log_fields()
    assert fields["decision"] == "send"
    assert fields["state"] == "LOCKED"
    assert "tick_ms" in fields

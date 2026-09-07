"""pod_mavlink.rx_runtime: the RX thread around the pure ``rx`` builders.

[PRD 7.2] the RX thread is the single writer of VehicleState/RCState. These tests use
a fake link that yields fake decoded-message objects --- no pymavlink, no socket ---
and assert the runtime turns them into the right contract values, drops malformed
ones without fabricating state, and starts/stops cleanly.
"""

from __future__ import annotations

import time

import pytest

from pod_config import ConfigOpenError, RCChannelMap
from pod_contracts import FlightMode
from pod_mavlink.rx_runtime import MavlinkRxRuntime

_RC_MAP = RCChannelMap(
    ai_enable_channel=6,
    lock_trigger_channel=7,
    kill_switch_channel=8,
    mission_mode_channel=9,
    high_threshold_us=1800,
)


class _FakeMsg:
    def __init__(self, msg_type: str, **fields: object) -> None:
        self._type = msg_type
        self.__dict__.update(fields)

    def get_type(self) -> str:
        return self._type


class _FakeLink:
    """Yields queued messages, then None forever. ``flightmode`` is settable."""

    def __init__(self) -> None:
        self._queue: list[object] = []
        self.flightmode = "STABILIZE"

    def feed(self, *msgs: object) -> None:
        self._queue.extend(msgs)

    def recv(self, *, timeout_s: float) -> object:
        if self._queue:
            return self._queue.pop(0)
        time.sleep(min(timeout_s, 0.005))
        return None


def _heartbeat(base_mode: int = 0) -> _FakeMsg:
    return _FakeMsg("HEARTBEAT", base_mode=base_mode, custom_mode=0)


def _wait_until(predicate, timeout_s: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return False


def test_initial_snapshot_is_failsafe_before_any_message() -> None:
    """[PRD 1.3 invariant 3] an unread VehicleState is already stale; RCState fails
    safe with kill_switch high."""
    link = _FakeLink()
    rx = MavlinkRxRuntime(link, boot_ts_ns=10_000_000_000, now_ns=time.monotonic_ns)
    vehicle, rc = rx.snapshot()
    assert vehicle.mode is FlightMode.UNKNOWN
    assert vehicle.heartbeat_ok(10_000_000_000) is False
    assert rc.kill_switch is True
    assert rc.ai_enable is False


def test_heartbeat_updates_mode_armed_and_heartbeat_clock() -> None:
    link = _FakeLink()
    link.flightmode = "GUIDED"
    rx = MavlinkRxRuntime(link, boot_ts_ns=0, now_ns=time.monotonic_ns)
    rx.start()
    try:
        link.feed(_heartbeat(base_mode=0x80))  # SAFETY_ARMED bit
        assert _wait_until(lambda: rx.snapshot()[0].mode is FlightMode.GUIDED)
        vehicle, _ = rx.snapshot()
        assert vehicle.armed is True
        assert rx.last_heartbeat_recv_ts_ns is not None
        assert vehicle.heartbeat_ok(rx.last_heartbeat_recv_ts_ns) is True
    finally:
        rx.stop()


def test_non_guided_flightmode_maps_to_other() -> None:
    link = _FakeLink()
    link.flightmode = "RTL"
    rx = MavlinkRxRuntime(link, boot_ts_ns=0)
    rx.start()
    try:
        link.feed(_heartbeat())
        assert _wait_until(lambda: rx.snapshot()[0].recv_ts_ns > 0)
        assert rx.snapshot()[0].mode is FlightMode.OTHER
    finally:
        rx.stop()


def test_attitude_and_local_position_update_only_their_fields() -> None:
    link = _FakeLink()
    rx = MavlinkRxRuntime(link, boot_ts_ns=0)
    rx.start()
    try:
        link.feed(
            _FakeMsg(
                "ATTITUDE",
                roll=0.5,
                pitch=-0.25,
                yaw=1.0,
                rollspeed=0.1,
                pitchspeed=0.2,
                yawspeed=0.3,
            ),
            _FakeMsg("LOCAL_POSITION_NED", x=10.0, y=-5.0, z=-20.0, vx=1.0, vy=0.0, vz=0.0),
        )
        assert _wait_until(lambda: rx.snapshot()[0].pos_north_m == 10.0)
        vehicle, _ = rx.snapshot()
        assert vehicle.roll_rad == 0.5
        assert vehicle.yaw_rate_rads == 0.3
        assert vehicle.pos_down_m == -20.0
        # ATTITUDE/LOCAL_POSITION never touch the heartbeat clock [invariant 3]
        assert vehicle.mode is FlightMode.UNKNOWN
        assert vehicle.heartbeat_ok(vehicle.recv_ts_ns) is False
    finally:
        rx.stop()


def test_rc_channels_decode_with_a_resolved_map() -> None:
    link = _FakeLink()
    rx = MavlinkRxRuntime(link, boot_ts_ns=0, rc_channels=_RC_MAP)
    rx.start()
    try:
        chans = {f"chan{i}_raw": 1000 for i in range(1, 11)}
        chans["chan6_raw"] = 2000  # ai_enable high
        chans["chan7_raw"] = 2000  # lock_trigger high
        link.feed(_FakeMsg("RC_CHANNELS", chancount=10, **chans))
        assert _wait_until(lambda: rx.snapshot()[1].ai_enable is True)
        _, rc = rx.snapshot()
        assert rc.lock_trigger is True
        assert rc.kill_switch is False
    finally:
        rx.stop()


def test_open_rc_channel_map_is_refused_not_guessed() -> None:
    """[house rule] channel numbers are OPEN in the shipped config; the runtime must
    refuse to decode RC against a guessed number."""
    link = _FakeLink()
    with pytest.raises(ConfigOpenError):
        MavlinkRxRuntime(link, boot_ts_ns=0, rc_channels=RCChannelMap())


def test_rc_channels_ignored_when_no_map_is_supplied() -> None:
    """rc_channels=None is a valid safe mode: RC stays at the fail-safe initial."""
    link = _FakeLink()
    rx = MavlinkRxRuntime(link, boot_ts_ns=0, rc_channels=None)
    rx.start()
    try:
        link.feed(
            _FakeMsg("RC_CHANNELS", chancount=8, **{f"chan{i}_raw": 2000 for i in range(1, 9)})
        )
        link.feed(_heartbeat())
        assert _wait_until(lambda: rx.snapshot()[0].recv_ts_ns > 0)
        _, rc = rx.snapshot()
        assert rc.kill_switch is True  # unchanged fail-safe initial
        assert rc.ai_enable is False
    finally:
        rx.stop()


def test_malformed_message_is_dropped_without_fabricating_state() -> None:
    """A HEARTBEAT missing base_mode must not produce a 'healthy' VehicleState."""
    link = _FakeLink()
    link.flightmode = "GUIDED"
    rx = MavlinkRxRuntime(link, boot_ts_ns=0)
    rx.start()
    try:
        link.feed(_FakeMsg("HEARTBEAT"))  # no base_mode / custom_mode
        assert _wait_until(lambda: rx.messages_ignored >= 1)
        vehicle, _ = rx.snapshot()
        assert vehicle.mode is FlightMode.UNKNOWN
        assert vehicle.heartbeat_ok(vehicle.recv_ts_ns) is False
    finally:
        rx.stop()


def test_unknown_message_type_is_counted_and_ignored() -> None:
    link = _FakeLink()
    rx = MavlinkRxRuntime(link, boot_ts_ns=0)
    rx.start()
    try:
        link.feed(_FakeMsg("VFR_HUD", airspeed=12.0))
        assert _wait_until(lambda: rx.messages_ignored >= 1)
        assert rx.snapshot()[0].mode is FlightMode.UNKNOWN
    finally:
        rx.stop()


def test_recv_error_does_not_kill_the_thread() -> None:
    class _AngryLink(_FakeLink):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def recv(self, *, timeout_s: float) -> object:
            self.calls += 1
            if self.calls == 1:
                raise OSError("transient link error")
            return super().recv(timeout_s=timeout_s)

    link = _AngryLink()
    link.flightmode = "GUIDED"
    rx = MavlinkRxRuntime(link, boot_ts_ns=0, recv_timeout_s=0.01)
    rx.start()
    try:
        link.feed(_heartbeat(base_mode=0x80))
        assert _wait_until(lambda: rx.snapshot()[0].mode is FlightMode.GUIDED)
        assert rx.running is True
    finally:
        rx.stop()


def test_clean_startup_and_shutdown() -> None:
    link = _FakeLink()
    rx = MavlinkRxRuntime(link, boot_ts_ns=0, join_timeout_s=2.0)
    assert rx.running is False
    rx.start()
    assert rx.running is True
    with pytest.raises(RuntimeError, match="already started"):
        rx.start()
    rx.stop()
    assert rx.running is False
    rx.stop()  # idempotent


def test_context_manager_starts_and_stops() -> None:
    link = _FakeLink()
    with MavlinkRxRuntime(link, boot_ts_ns=0) as rx:
        assert rx.running is True
    assert rx.running is False

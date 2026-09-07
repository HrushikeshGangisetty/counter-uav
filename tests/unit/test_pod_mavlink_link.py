"""pod_mavlink.MavlinkLink.send(): transmits nothing when SILENT, and the right
SET_POSITION_TARGET_LOCAL_NED fields otherwise. [PRD 4.3]

No pymavlink installed in this environment (it is the 'sitl' extra, not a dev
dependency), so these tests inject a fake connection double directly onto
link._conn rather than opening a real one --- see MavlinkLink.__init__'s docstring
note on why _conn is a plain, not name-mangled, attribute.
"""

from __future__ import annotations

import pytest

from pod_contracts import CommandDecision, PodState, StateOutput
from pod_mavlink import (
    BAUD_RATE,
    COMMAND_PERIOD_S,
    COMMAND_RATE_HZ,
    MAV_FRAME_BODY_NED,
    MavlinkLink,
)
from simulation.mocks import make_velocity_command


class _FakeMav:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    def set_position_target_local_ned_send(self, **fields: object) -> None:
        self.sent.append(fields)


class _FakeConn:
    def __init__(self) -> None:
        self.mav = _FakeMav()
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _linked() -> tuple[MavlinkLink, _FakeConn]:
    link = MavlinkLink(device="udp:127.0.0.1:14550")
    fake = _FakeConn()
    link._conn = fake  # test-only injection; see module docstring
    return link, fake


def test_command_rate_and_period_are_consistent() -> None:
    assert COMMAND_RATE_HZ == 20
    assert pytest.approx(0.05) == COMMAND_PERIOD_S


def test_default_baud_matches_the_closed_decision() -> None:
    """docs/decisions/0004-mavlink-baud-115200.md."""
    link = MavlinkLink(device="/dev/ttyAMA0")
    assert link.baud == BAUD_RATE == 115200


def test_send_transmits_nothing_when_silent() -> None:
    link, fake = _linked()
    output = StateOutput(
        state=PodState.LOST, decision=CommandDecision.SILENT, command=None, reason="target_lost"
    )
    sent = link.send(output, time_boot_ms=0, target_system=1, target_component=1)
    assert sent is False
    assert fake.mav.sent == []


def test_send_transmits_the_setpoint_when_send() -> None:
    link, fake = _linked()
    command = make_velocity_command()
    output = StateOutput(
        state=PodState.LOCKED, decision=CommandDecision.SEND, command=command, reason="pursuing"
    )
    sent = link.send(output, time_boot_ms=42, target_system=1, target_component=1)
    assert sent is True
    assert len(fake.mav.sent) == 1
    fields = fake.mav.sent[0]
    assert fields["coordinate_frame"] == MAV_FRAME_BODY_NED
    assert fields["vx"] == command.vx_ms
    assert fields["time_boot_ms"] == 42


def test_send_never_substitutes_zero_velocity() -> None:
    """[PRD 4.3] SILENT with command=None must not become a sent zero-velocity
    setpoint, even if a caller constructs a malformed StateOutput."""
    link, fake = _linked()
    output = StateOutput(
        state=PodState.IDLE, decision=CommandDecision.SILENT, command=None, reason="idle"
    )
    link.send(output, time_boot_ms=0, target_system=1, target_component=1)
    assert fake.mav.sent == []


def test_send_before_open_raises() -> None:
    link = MavlinkLink(device="/dev/ttyAMA0")
    command = make_velocity_command()
    output = StateOutput(
        state=PodState.LOCKED, decision=CommandDecision.SEND, command=command, reason="pursuing"
    )
    with pytest.raises(RuntimeError, match="not open"):
        link.send(output, time_boot_ms=0, target_system=1, target_component=1)


def test_open_without_pymavlink_installed_raises_a_clear_error() -> None:
    try:
        import pymavlink  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("pymavlink is installed in this environment (the 'sitl' extra); "
                     "the ImportError path cannot be exercised here")
    link = MavlinkLink(device="udp:127.0.0.1:14550")
    with pytest.raises(RuntimeError, match="pymavlink is not installed"):
        link.open()


def test_close_releases_the_connection() -> None:
    link, fake = _linked()
    link.close()
    assert fake.closed is True
    assert link._conn is None

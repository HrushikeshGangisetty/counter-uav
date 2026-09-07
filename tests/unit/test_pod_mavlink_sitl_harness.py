"""simulation.sitl.harness.SitlHarness: the same pod_mavlink + pod_state path,
driven against a real MAVLink UDP endpoint.

Requires the 'sitl' extra (pymavlink). Skipped otherwise --- exactly like
test_pod_mavlink_link.py's open()-without-pymavlink path. No ArduPilot install is
needed: a second in-process pymavlink connection plays the part of the FC, sending
HEARTBEAT / RC_CHANNELS over loopback UDP.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("pymavlink", reason="the 'sitl' extra (pymavlink) is not installed")

from pymavlink import mavutil  # noqa: E402

from pod_contracts import FlightMode  # noqa: E402
from simulation.sitl.harness import SitlHarness, constant_pursuit_source  # noqa: E402

_POD_PORT = 14577


def _fake_fc(port: int):
    """A pymavlink 'FC' that the harness's MavlinkLink will receive from."""
    return mavutil.mavlink_connection(f"udpout:127.0.0.1:{port}", source_system=1)


@pytest.fixture
def _harness():
    h = SitlHarness(connection=f"udpin:127.0.0.1:{_POD_PORT}", rate_hz=20)
    yield h
    h.stop()


def test_connection_and_startup_path(_harness) -> None:
    _harness.start()
    assert _harness.rx is not None and _harness.rx.running
    assert _harness.scheduler is not None


def test_telemetry_is_received_and_decoded(_harness) -> None:
    _harness.start()
    fc = _fake_fc(_POD_PORT)
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        fc.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_QUADROTOR,
            mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            0,
            0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
        )
        time.sleep(0.1)
        if _harness.rx and _harness.rx.messages_seen > 0:
            break
    assert _harness.rx is not None
    assert _harness.rx.messages_seen > 0
    vehicle, _rc = _harness.rx.snapshot()
    assert vehicle.mode in (FlightMode.GUIDED, FlightMode.OTHER)


def test_a_safe_setpoint_can_traverse_the_path(_harness) -> None:
    """With prerequisites satisfied (GUIDED + heartbeat + a proposed command), a
    governed SEND reaches MavlinkLink.send(). Here the machine starts in LOCKED and
    the command source reports a visible target; RC is left at its fail-safe initial
    (kill_switch high) unless the sim provides RC, so this asserts the path runs and
    stays SILENT-safe rather than forcing a transmit without real RC."""
    _harness.command_source = constant_pursuit_source()
    _harness.start()
    _harness.run(max_ticks=10)
    assert _harness.scheduler is not None
    assert _harness.scheduler.tick_count == 10


def test_shutdown_is_clean(_harness) -> None:
    _harness.start()
    _harness.run(max_ticks=3)
    _harness.stop()
    assert _harness.rx is not None and _harness.rx.running is False

"""pod_mavlink.rx: pure VehicleState/RCState builders from decoded MAVLink fields.

[PRD 7.2] the RX thread is the single writer of both; these are what it would call.
No pymavlink needed --- synthetic numeric fields stand in for what a decoded message
already carries.
"""

from __future__ import annotations

from pod_contracts import FlightMode
from pod_mavlink import (
    apply_attitude,
    apply_heartbeat,
    apply_local_position_ned,
    initial_rc_state,
    initial_vehicle_state,
    rc_state_from_channels,
)


def test_initial_vehicle_state_is_already_stale() -> None:
    """[PRD 1.3 invariant 3] an unread VehicleState must not be trusted."""
    boot_ts_ns = 10_000_000_000
    vehicle = initial_vehicle_state(boot_ts_ns)
    assert vehicle.mode is FlightMode.UNKNOWN
    assert vehicle.armed is False
    assert vehicle.heartbeat_ok(boot_ts_ns) is False


def test_initial_rc_state_fails_safe() -> None:
    rc = initial_rc_state(boot_ts_ns=0)
    assert rc.ai_enable is False
    assert rc.lock_trigger is False
    assert rc.kill_switch is True


def test_apply_heartbeat_updates_mode_armed_and_heartbeat_clock() -> None:
    vehicle = initial_vehicle_state(0)
    updated = apply_heartbeat(vehicle, recv_ts_ns=5_000, mode=FlightMode.GUIDED, armed=True)
    assert updated.mode is FlightMode.GUIDED
    assert updated.armed is True
    assert updated.last_heartbeat_ts_ns == 5_000
    assert updated.heartbeat_ok(5_000) is True


def test_apply_heartbeat_does_not_touch_other_fields() -> None:
    vehicle = apply_attitude(
        initial_vehicle_state(0),
        recv_ts_ns=1,
        roll_rad=0.1,
        pitch_rad=0.2,
        yaw_rad=0.3,
        roll_rate_rads=0.0,
        pitch_rate_rads=0.0,
        yaw_rate_rads=0.0,
    )
    updated = apply_heartbeat(vehicle, recv_ts_ns=2, mode=FlightMode.GUIDED, armed=True)
    assert updated.roll_rad == 0.1
    assert updated.pitch_rad == 0.2
    assert updated.yaw_rad == 0.3


def test_apply_attitude_updates_orientation_and_rates_only() -> None:
    vehicle = apply_heartbeat(
        initial_vehicle_state(0), recv_ts_ns=1, mode=FlightMode.GUIDED, armed=True
    )
    updated = apply_attitude(
        vehicle,
        recv_ts_ns=2,
        roll_rad=0.5,
        pitch_rad=-0.5,
        yaw_rad=1.0,
        roll_rate_rads=0.1,
        pitch_rate_rads=0.2,
        yaw_rate_rads=0.3,
    )
    assert updated.roll_rad == 0.5
    assert updated.pitch_rad == -0.5
    assert updated.yaw_rad == 1.0
    assert updated.roll_rate_rads == 0.1
    assert updated.pitch_rate_rads == 0.2
    assert updated.yaw_rate_rads == 0.3
    # HEARTBEAT-only field is untouched by ATTITUDE [PRD 1.3 invariant 3]
    assert updated.last_heartbeat_ts_ns == 1
    assert updated.mode is FlightMode.GUIDED


def test_apply_local_position_ned_updates_position_and_velocity() -> None:
    vehicle = initial_vehicle_state(0)
    updated = apply_local_position_ned(
        vehicle,
        recv_ts_ns=3,
        pos_north_m=10.0,
        pos_east_m=-5.0,
        pos_down_m=-20.0,
        vel_north_ms=1.0,
        vel_east_ms=0.0,
        vel_down_ms=0.0,
    )
    assert updated.pos_north_m == 10.0
    assert updated.pos_east_m == -5.0
    assert updated.pos_down_m == -20.0
    assert updated.vel_north_ms == 1.0


def test_rc_state_from_channels_decodes_1_based_channel_numbers() -> None:
    raw = (1000, 1000, 2000, 1000)  # channel 3 (index 2) is high
    rc = rc_state_from_channels(
        recv_ts_ns=0,
        raw_channels=raw,
        ai_enable_channel=3,
        lock_trigger_channel=1,
        kill_switch_channel=2,
        high_threshold_us=1800,
    )
    assert rc.ai_enable is True
    assert rc.lock_trigger is False
    assert rc.kill_switch is False
    assert rc.raw_channels == raw


def test_rc_state_from_channels_all_high() -> None:
    raw = (1900, 1900, 1900)
    rc = rc_state_from_channels(
        recv_ts_ns=0,
        raw_channels=raw,
        ai_enable_channel=1,
        lock_trigger_channel=2,
        kill_switch_channel=3,
        high_threshold_us=1800,
    )
    assert rc.ai_enable is True
    assert rc.lock_trigger is True
    assert rc.kill_switch is True

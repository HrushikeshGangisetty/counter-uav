"""pod_mavlink.setpoint: outbound SET_POSITION_TARGET_LOCAL_NED, built pure.

[PRD 5.4] MAV_FRAME_BODY_NED, type_mask enabling ONLY vx, vy, vz, yaw_rate ---
position and acceleration bits masked out.
"""

from __future__ import annotations

from pod_mavlink import (
    MAV_FRAME_BODY_NED,
    SETPOINT_TYPE_MASK,
    SETPOINT_TYPE_MASK_FIELDS,
    build_set_position_target_local_ned,
)
from simulation.mocks import make_velocity_command


def test_setpoint_type_mask_fields_are_exactly_velocity_and_yaw_rate() -> None:
    assert set(SETPOINT_TYPE_MASK_FIELDS) == {"vx", "vy", "vz", "yaw_rate"}


def test_type_mask_enables_only_the_documented_fields() -> None:
    """type_mask bits are 1 = ignored [MAVLink common.xml POSITION_TARGET_TYPEMASK].
    Every enabled field's bit must be 0; every other field's bit must be 1."""
    bit = {
        "x": 1, "y": 2, "z": 4,
        "vx": 8, "vy": 16, "vz": 32,
        "ax": 64, "ay": 128, "az": 256,
        "yaw": 1024, "yaw_rate": 2048,
    }
    for name, value in bit.items():
        ignored = (SETPOINT_TYPE_MASK & value) != 0
        should_be_enabled = name in SETPOINT_TYPE_MASK_FIELDS
        assert ignored is not should_be_enabled, f"{name} enabled={not ignored}"


def test_frame_is_body_ned() -> None:
    """[MAVLink common.xml MAV_FRAME enum] MAV_FRAME_BODY_NED == 8."""
    assert MAV_FRAME_BODY_NED == 8


def test_build_carries_the_velocity_command_through() -> None:
    command = make_velocity_command()
    fields = build_set_position_target_local_ned(
        command, time_boot_ms=1234, target_system=1, target_component=1
    )
    assert fields["coordinate_frame"] == MAV_FRAME_BODY_NED
    assert fields["type_mask"] == SETPOINT_TYPE_MASK
    assert fields["vx"] == command.vx_ms
    assert fields["vy"] == command.vy_ms
    assert fields["vz"] == command.vz_ms
    assert fields["yaw_rate"] == command.yaw_rate_rads
    assert fields["time_boot_ms"] == 1234
    assert fields["target_system"] == 1
    assert fields["target_component"] == 1


def test_build_is_deterministic() -> None:
    command = make_velocity_command()
    a = build_set_position_target_local_ned(
        command, time_boot_ms=0, target_system=1, target_component=1
    )
    b = build_set_position_target_local_ned(
        command, time_boot_ms=0, target_system=1, target_component=1
    )
    assert a == b

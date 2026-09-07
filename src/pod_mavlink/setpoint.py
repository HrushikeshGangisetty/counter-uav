"""Outbound SET_POSITION_TARGET_LOCAL_NED, built pure. [PRD 5.4]

No pymavlink here. This module only assembles the plain field values the MAVLink
message needs; pymavlink is lazily imported inside MavlinkLink.send() (link.py),
which is the only thing that actually hands these fields to a socket. That split is
what makes the encoding testable with no hardware and no pymavlink installed.

MAV_FRAME_BODY_NED and the POSITION_TARGET_TYPEMASK ignore-bit values below are
MAVLink common.xml protocol constants --- fixed by the wire format itself, not a
project decision, so hard-coding them is not "inventing a number" the house rule
warns about.
"""

from __future__ import annotations

from pod_contracts import VelocityCommand

#: [PRD 5.4] SET_POSITION_TARGET_LOCAL_NED in MAV_FRAME_BODY_NED with the type_mask
#: enabling ONLY these fields. "Position and acceleration bits must be masked out or
#: the FC will interpret the command very differently from what you intended."
SETPOINT_TYPE_MASK_FIELDS = ("vx", "vy", "vz", "yaw_rate")

#: [MAVLink common.xml, MAV_FRAME enum] Body-frame NED, matching pod_contracts'
#: velocity/yaw_rate units [docs/contracts.md "Units"].
MAV_FRAME_BODY_NED = 8

#: [MAVLink common.xml, POSITION_TARGET_TYPEMASK enum] one bit per field that, when
#: set, means "ignore this field". Fixed by the protocol, not by this project.
_IGNORE_BIT = {
    "x": 1,
    "y": 2,
    "z": 4,
    "vx": 8,
    "vy": 16,
    "vz": 32,
    "ax": 64,
    "ay": 128,
    "az": 256,
    "yaw": 1024,
    "yaw_rate": 2048,
}


def _build_type_mask() -> int:
    """[PRD 5.4] "position and acceleration bits must be masked out." Ignore every
    field NOT in SETPOINT_TYPE_MASK_FIELDS --- the single place that list is
    defined --- so the mask can never drift from what the README/contract says is
    enabled."""
    enabled = set(SETPOINT_TYPE_MASK_FIELDS)
    ignored = set(_IGNORE_BIT) - enabled
    mask = 0
    for name in ignored:
        mask |= _IGNORE_BIT[name]
    return mask


#: Computed once from SETPOINT_TYPE_MASK_FIELDS: enables ONLY vx, vy, vz, yaw_rate.
SETPOINT_TYPE_MASK = _build_type_mask()


def build_set_position_target_local_ned(
    command: VelocityCommand,
    *,
    time_boot_ms: int,
    target_system: int,
    target_component: int,
) -> dict[str, object]:
    """Field values for one SET_POSITION_TARGET_LOCAL_NED message. PURE.

    ``target_system``/``target_component`` are not defaulted: MAVLink system/
    component addressing is not stated in any project document, so the caller (the
    eventual M3 control loop, or a test) must supply it rather than this module
    guessing a conventional "1".

    The x, y, z, afx, afy, afz and yaw fields below are filled with 0.0 only because
    ``type_mask`` marks every one of them ignored [PRD 5.4] --- the FC never reads
    them. That is a protocol filler value, not a fabricated measurement.
    """
    return {
        "time_boot_ms": time_boot_ms,
        "target_system": target_system,
        "target_component": target_component,
        "coordinate_frame": MAV_FRAME_BODY_NED,
        "type_mask": SETPOINT_TYPE_MASK,
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "vx": command.vx_ms,
        "vy": command.vy_ms,
        "vz": command.vz_ms,
        "afx": 0.0,
        "afy": 0.0,
        "afz": 0.0,
        "yaw": 0.0,
        "yaw_rate": command.yaw_rate_rads,
    }

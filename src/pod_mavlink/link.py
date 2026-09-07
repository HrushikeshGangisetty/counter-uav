"""The single owner of the FC serial handle."""

from __future__ import annotations

from pod_contracts import StateOutput

#: ✅ CLOSED 2026-09-07 at 115200 (CF-04 / OD-07). arch v1.0's figure is adopted; the
#: PRD's "raise to 921600" is NOT adopted, so the [PRD 6.2] latency budget stands as
#: written (MAVLink serialise + UART ~1 ms typical, 6 ms worst case, computed at
#: 115200). Reversible if M3 measurement shows link-induced spikes.
#: See docs/decisions/0004-mavlink-baud-115200.md.
BAUD_RATE = 115200

#: [PRD 1.1], [ARCH Control]
COMMAND_RATE_HZ = 20

#: [PRD 5.4] trim SRx_* to only these. At 115200 this is the mitigation, not an
#: optimisation. Specific rate VALUES are OPEN (OD-07b) --- tuned at M3 against
#: measured link utilisation, never guessed.
CONSUMED_STREAMS = (
    "HEARTBEAT",
    "ATTITUDE",
    "LOCAL_POSITION_NED",
    "RC_CHANNELS",
    "VFR_HUD",
)

#: [PRD 5.4] SET_POSITION_TARGET_LOCAL_NED in MAV_FRAME_BODY_NED with the type_mask
#: enabling ONLY these fields. "Position and acceleration bits must be masked out or
#: the FC will interpret the command very differently from what you intended."
SETPOINT_TYPE_MASK_FIELDS = ("vx", "vy", "vz", "yaw_rate")


class MavlinkLink:
    """Holds the serial handle. There is exactly one of these in the process.

    ⚠ NOT IMPLEMENTED --- M2 (SITL) then M3 (real FC), Person A.

    Contract when implemented:
      * the ONLY object in the codebase that opens or writes the FC serial port
        [PRD 1.3 invariant 7];
      * the RX thread is the SINGLE WRITER of VehicleState and RCState [PRD 7.2];
      * ``send`` accepts a StateOutput and transmits nothing at all when
        decision is SILENT --- it never substitutes a zero-velocity setpoint
        [PRD 4.3];
      * a watchdog forces silence if the control thread dies: "a live process with a
        dead control thread is the dangerous case" [PRD 5.5].
    """

    def __init__(self, device: str, baud: int = BAUD_RATE) -> None:
        self.device = device
        self.baud = baud

    def open(self) -> None:
        raise NotImplementedError("pod_mavlink.MavlinkLink.open: M2 / Person A")

    def send(self, output: StateOutput) -> None:
        raise NotImplementedError("pod_mavlink.MavlinkLink.send: M2 / Person A")

    def close(self) -> None:
        raise NotImplementedError("pod_mavlink.MavlinkLink.close: M2 / Person A")

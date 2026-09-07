"""The single owner of the FC serial handle."""

from __future__ import annotations

from typing import Any

from pod_contracts import CommandDecision, StateOutput

from .setpoint import SETPOINT_TYPE_MASK_FIELDS, build_set_position_target_local_ned

__all__ = [
    "BAUD_RATE",
    "COMMAND_PERIOD_S",
    "COMMAND_RATE_HZ",
    "CONSUMED_STREAMS",
    "SETPOINT_TYPE_MASK_FIELDS",
    "MavlinkLink",
]

#: ✅ CLOSED 2026-09-07 at 115200 (CF-04 / OD-07). arch v1.0's figure is adopted; the
#: PRD's "raise to 921600" is NOT adopted, so the [PRD 6.2] latency budget stands as
#: written (MAVLink serialise + UART ~1 ms typical, 6 ms worst case, computed at
#: 115200). Reversible if M3 measurement shows link-induced spikes.
#: See docs/decisions/0004-mavlink-baud-115200.md.
BAUD_RATE = 115200

#: [PRD 1.1], [ARCH Control]
COMMAND_RATE_HZ = 20

#: Nominal period between setpoints at COMMAND_RATE_HZ, in seconds --- arithmetic on
#: an already-closed value [PRD 1.1], not a new decision. The M3 control loop's
#: scheduler (not built in this slice; it needs a live serial port and a running
#: process to schedule) is expected to call MavlinkLink.send() on this cadence.
COMMAND_PERIOD_S = 1.0 / COMMAND_RATE_HZ

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


class MavlinkLink:
    """Holds the serial handle. There is exactly one of these in the process.

    [PRD 1.3 invariant 7] the ONLY object in the codebase that opens or writes the FC
    serial port; enforced by review, tests/architecture/test_serial_ownership.py (no
    other module may import pymavlink/pyserial/mavutil) and electrically by the
    ADuM1201 galvanic isolator.

    ⚠ Not yet implemented this slice: the RX thread (single writer of VehicleState /
    RCState [PRD 7.2], via pod_mavlink.rx) and the M3 control-loop watchdog ("a live
    process with a dead control thread is the dangerous case" [PRD 5.5]) both need a
    live serial port and a running process to thread against --- that is SITL/M3
    integration work, not this module's outbound send() path.
    """

    def __init__(self, device: str, baud: int = BAUD_RATE) -> None:
        self.device = device
        self.baud = baud
        #: Plain attribute, not a private name-mangled one, so tests can inject a
        #: fake connection (anything exposing `.mav.set_position_target_local_ned_send`
        #: and `.close()`) without needing pymavlink installed.
        self._conn: Any = None

    def open(self) -> None:
        """Open the serial connection. Requires the 'sitl' extra (pymavlink) ---
        lazily imported here, not at module level, so importing pod_mavlink itself
        never requires pymavlink [README "No hardware required"]."""
        if self._conn is not None:
            raise RuntimeError("pod_mavlink.MavlinkLink.open: already open")
        try:
            from pymavlink import mavutil
        except ImportError as exc:
            raise RuntimeError(
                "pod_mavlink.MavlinkLink.open: pymavlink is not installed. Install "
                "the 'sitl' extra: pip install -e '.[sitl]'"
            ) from exc
        self._conn = mavutil.mavlink_connection(self.device, baud=self.baud)

    def send(
        self,
        output: StateOutput,
        *,
        time_boot_ms: int,
        target_system: int,
        target_component: int,
    ) -> bool:
        """Transmit ``output.command`` as SET_POSITION_TARGET_LOCAL_NED, or nothing.

        [PRD 4.3] transmits nothing at all when decision is SILENT --- never a
        zero-velocity substitute. Returns True if a message was sent, False if
        SILENT was honoured, so a caller (or a test) can assert on it directly rather
        than inspecting the fake connection.

        ``output`` is expected to already have passed through
        pod_state.governor.govern() [PRD 1.3 invariant 1] --- this method does not
        call govern() itself (pod_mavlink does not import pod_state: StateOutput is
        the documented hand-off point between them, not a function call across it
        [docs/contracts.md registry]). It still only ever acts on ``output.decision``,
        so a caller that forgot to govern gets the same silent-by-default behaviour
        for any non-SEND decision.
        """
        if output.decision is not CommandDecision.SEND or output.command is None:
            return False
        if self._conn is None:
            raise RuntimeError("pod_mavlink.MavlinkLink.send: link is not open")
        fields = build_set_position_target_local_ned(
            output.command,
            time_boot_ms=time_boot_ms,
            target_system=target_system,
            target_component=target_component,
        )
        self._conn.mav.set_position_target_local_ned_send(**fields)
        return True

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

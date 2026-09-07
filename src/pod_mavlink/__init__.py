"""pod_mavlink --- the serial port: RX thread, governor hand-off, TX.

Owner: Person A (Hrushikesh), exclusively.
[PRD 2.3] Must never import: GStreamer.

⚠ HARD INVARIANT 7 [PRD 1.3]: "Exactly one software module holds the serial handle to
the flight controller. Nothing else may write to it." [PRD 7.2] "If you find
yourself wanting a second writer, the answer is no."

That invariant is enforced three ways: by review, by
tests/architecture/test_serial_ownership.py (no other module may import pymavlink or
pyserial), and electrically by the ADuM1201 galvanic isolator [PRD 2.1].

Layers, from pure to running (decision 0021, decision 0022):

* ``setpoint.py`` / ``rx.py`` --- pure encode/decode, no pymavlink, synthetic-testable.
* ``link.py`` --- ``MavlinkLink``, the one object that opens/reads/writes the port.
* ``rx_runtime.py`` --- ``MavlinkRxRuntime``, the RX thread; single writer of
  ``VehicleState`` / ``RCState`` [PRD 7.2].
* ``scheduler.py`` --- ``FixedRateScheduler``, the 20 Hz driver [PRD 1.1].
* ``control_loop.py`` --- ``ControlLoop``, one governed cycle: rx -> ``pod_state`` ->
  ``MavlinkLink.send()``. The governor stays the final authority [PRD 1.3 invariant 1].
* ``supervisor.py`` --- ``ControlSupervisor``, the [PRD 5.5] watchdog: owns the
  control thread, and on unexpected exit or no tick progress it stops the scheduler
  and reports. It never sends, never commands (decision 0023).
"""

from __future__ import annotations

from .control_loop import (
    CommandSource,
    ControlLoop,
    CycleReport,
    PerceptionInputs,
    null_command_source,
)
from .link import (
    BAUD_RATE,
    COMMAND_PERIOD_S,
    COMMAND_RATE_HZ,
    CONSUMED_STREAMS,
    SETPOINT_TYPE_MASK_FIELDS,
    MavlinkLink,
)
from .rx import (
    apply_attitude,
    apply_heartbeat,
    apply_local_position_ned,
    initial_rc_state,
    initial_vehicle_state,
    rc_state_from_channels,
)
from .rx_runtime import RX_MESSAGE_TYPES, MavlinkRxRuntime, default_mode_decoder
from .scheduler import FixedRateScheduler
from .setpoint import (
    MAV_FRAME_BODY_NED,
    SETPOINT_TYPE_MASK,
    build_set_position_target_local_ned,
)
from .supervisor import (
    ControlHealth,
    ControlSupervisor,
    SupervisorReport,
    require_watchdog_timeout_ns,
    watchdog_timeout_ns_from_envelope,
)

__all__ = [
    "BAUD_RATE",
    "COMMAND_PERIOD_S",
    "COMMAND_RATE_HZ",
    "CONSUMED_STREAMS",
    "MAV_FRAME_BODY_NED",
    "RX_MESSAGE_TYPES",
    "SETPOINT_TYPE_MASK",
    "SETPOINT_TYPE_MASK_FIELDS",
    "CommandSource",
    "ControlHealth",
    "ControlLoop",
    "ControlSupervisor",
    "CycleReport",
    "FixedRateScheduler",
    "MavlinkLink",
    "MavlinkRxRuntime",
    "PerceptionInputs",
    "SupervisorReport",
    "apply_attitude",
    "apply_heartbeat",
    "apply_local_position_ned",
    "build_set_position_target_local_ned",
    "default_mode_decoder",
    "initial_rc_state",
    "initial_vehicle_state",
    "null_command_source",
    "rc_state_from_channels",
    "require_watchdog_timeout_ns",
    "watchdog_timeout_ns_from_envelope",
]

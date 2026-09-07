"""pod_mavlink --- the serial port: RX thread, governor hand-off, TX.

Owner: Person A (Hrushikesh), exclusively.
[PRD 2.3] Must never import: GStreamer.

⚠ HARD INVARIANT 7 [PRD 1.3]: "Exactly one software module holds the serial handle to
the flight controller. Nothing else may write to it." [PRD 7.2] "If you find
yourself wanting a second writer, the answer is no."

That invariant is enforced three ways: by review, by
tests/architecture/test_serial_ownership.py (no other module may import pymavlink or
pyserial), and electrically by the ADuM1201 galvanic isolator [PRD 2.1].
"""

from __future__ import annotations

from .link import (
    BAUD_RATE,
    COMMAND_RATE_HZ,
    CONSUMED_STREAMS,
    SETPOINT_TYPE_MASK_FIELDS,
    MavlinkLink,
)

__all__ = [
    "BAUD_RATE",
    "COMMAND_RATE_HZ",
    "CONSUMED_STREAMS",
    "SETPOINT_TYPE_MASK_FIELDS",
    "MavlinkLink",
]

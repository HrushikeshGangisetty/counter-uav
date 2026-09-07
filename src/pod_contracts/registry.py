"""Registry of cross-module message types.

Exists so [PRD 2.3, 7.2] --- "every cross-module message carries the capture
timestamp and frame sequence number" --- is machine-checkable rather than only
documented. tests/contracts/test_message_stamps.py walks this registry.

A message satisfies the rule either by carrying a FrameMeta (which holds both
fields) or by carrying capture_ts_ns and frame_seq directly (TelemetryFrame does the
latter, because its JSON wire form is flat).

Adding a cross-module message means adding it here. A message NOT in this registry
is, by definition, module-internal.
"""

from __future__ import annotations

from .detection import TrackFrame
from .geometry import LineOfSight
from .guidance import GuidanceInput, VelocityCommand
from .latency import LatencySample
from .state import StateInput, StateOutput
from .telemetry import TelemetryFrame

#: Messages that must carry capture timestamp + frame sequence number.
CROSS_MODULE_MESSAGES = (
    TrackFrame,
    LineOfSight,
    GuidanceInput,
    VelocityCommand,
    LatencySample,
    TelemetryFrame,
)

#: StateInput/StateOutput are exempt and this is deliberate, not an oversight:
#: StateInput.frame is Optional because the state machine must still run a tick when
#: no frame arrived (that is exactly when it must go SILENT), and StateOutput's
#: stamping rides on its embedded VelocityCommand. Both are listed here so the
#: exemption is explicit and reviewable.
STAMP_EXEMPT_MESSAGES = (StateInput, StateOutput)

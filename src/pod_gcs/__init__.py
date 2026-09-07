"""pod_gcs --- pod-side WebSocket telemetry server, RTSP video, read-only state view.

Owner: Person A (Hrushikesh) [Team 2026-09-07].
[PRD 2.3] Must never import: pymavlink.

That import ban is the pod-side half of the two-link topology [PRD 2.4]: FC telemetry
reaches the ground station over the FC's OWN radio, never relayed through the pod,
"because a pod brownout would blind the operator to the aircraft at exactly the
moment they most need to see it."

⚠ CF-12 / OD-14 OPEN: the interim ground station is the existing KFT Android GCS,
which has a full bidirectional MAVLink stack. While it is in use the receive-only
requirement backing hard invariant 7 is NOT met. This is an accepted, expiring
exception --- see docs/decisions/0007-interim-gcs-invariant-exception.md, which is
PROPOSED and awaiting sign-off, not closed.
"""

from __future__ import annotations

from .server import ALLOWED_GCS_COMMANDS, TELEMETRY_RATE_HZ, TelemetryServer

__all__ = ["ALLOWED_GCS_COMMANDS", "TELEMETRY_RATE_HZ", "TelemetryServer"]

"""Pod-side telemetry server."""

from __future__ import annotations

from pod_contracts import ALLOWED_GCS_COMMANDS, TelemetryFrame

#: [PRD 2.4, 5.5], [ARCH Comms protocols]
TELEMETRY_RATE_HZ = 10

__all__ = ["ALLOWED_GCS_COMMANDS", "TELEMETRY_RATE_HZ", "TelemetryServer"]


class TelemetryServer:
    """WebSocket telemetry out, narrow command surface in.

    ⚠ NOT IMPLEMENTED --- M4, Person A.

    Contract when implemented:
      * outbound: TelemetryFrame as JSON at ~10 Hz [PRD 2.4];
      * inbound: ONLY the commands in ALLOWED_GCS_COMMANDS --- lock, unlock and
        pre-takeoff mode_set. [PRD 5.5] "It must not be able to change break-off
        radius, velocity envelopes or mission mode in flight, and it must not be able
        to bypass the safety governor." Anything else is rejected, not ignored;
      * imports no pymavlink, ever [PRD 2.3].
    """

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def publish(self, frame: TelemetryFrame) -> None:
        raise NotImplementedError("pod_gcs.TelemetryServer.publish: M4 / Person A")

    def handle_command(self, name: str, payload: dict) -> None:
        raise NotImplementedError("pod_gcs.TelemetryServer.handle_command: M4 / Person A")

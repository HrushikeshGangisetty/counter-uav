"""Frame metadata: the timestamp/sequence pair every cross-module message carries.

[PRD 2.3, 7.2] "Every cross-module message carries the capture timestamp and frame
sequence number, so any consumer can independently reject stale data rather than
trusting its producer."

Owner: Person A. Producer: pod_perception. Consumers: every downstream module.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Clock used for capture_ts_ns. CLOCK_MONOTONIC on the pod host, in nanoseconds,
#: stamped at DMA into memory by the RP1 I/O controller [PRD 2.2]. Monotonic, not
#: wall-clock: it is used for age arithmetic, never for calendar time.
CAPTURE_CLOCK = "CLOCK_MONOTONIC"


@dataclass(frozen=True, slots=True)
class FrameMeta:
    """Identity and timing of one captured frame.

    Attributes:
        camera_id: 0 or 1. Which CSI-2 port the frame came from.
        frame_seq: Monotonically increasing, per camera_id, starting at 0 at pipeline
            start. Never reused, never reset in flight. Gaps mean dropped frames and
            are expected (appsink is drop=true max-buffers=1 [PRD 5.2]).
        capture_ts_ns: CLOCK_MONOTONIC nanoseconds at DMA [PRD 2.2].
        width_px, height_px: Sensor-native frame size (1456x1088 baseline [PRD 2.1]).
    """

    camera_id: int
    frame_seq: int
    capture_ts_ns: int
    width_px: int
    height_px: int

    def age_ns(self, now_ns: int) -> int:
        """Age of this frame against a CLOCK_MONOTONIC reading. Pure."""
        return now_ns - self.capture_ts_ns

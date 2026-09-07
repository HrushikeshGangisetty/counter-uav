"""pod_state --- state machine, envelope clamps, rate limits, safety governor.

Owner: Person A (Hrushikesh).
[PRD 2.3] Must never import: GStreamer, pymavlink.
[PRD 2.3, 7.2] PURE: no I/O, no threads, no globals.
"""

from __future__ import annotations

from .governor import GOVERNOR_PRECONDITIONS, govern
from .machine import TRANSITIONS, Transition, step

__all__ = ["GOVERNOR_PRECONDITIONS", "TRANSITIONS", "Transition", "govern", "step"]

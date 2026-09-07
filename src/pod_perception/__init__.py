"""pod_perception --- GStreamer pipeline construction and the appsink callback.

Owner: Person A (Hrushikesh).
[PRD 2.3] Must never import: pymavlink, control logic. That means no pod_mavlink,
no pod_guidance, no pod_state. Enforced by tests/architecture/.

Implementation-0 status: the pipeline description is declared as data (pipeline.py)
so the shape is reviewable and testable without hardware; construction and the
appsink callback are M1 and are blocked on the Pi 5 + AI HAT+ + IMX296 hardware.
"""

from __future__ import annotations

from .pipeline import APPSINK_PROPERTIES, PIPELINE_ELEMENTS, build_pipeline, describe_pipeline

__all__ = ["APPSINK_PROPERTIES", "PIPELINE_ELEMENTS", "build_pipeline", "describe_pipeline"]

"""Ground-truth and prediction box types for evaluation.

Reuses ``pod_contracts.BBox`` for geometry (pixels, top-left origin) rather than
redefining it. These are evaluation-time value objects, not cross-module runtime
messages, so they stay local to ``tools.ml`` --- the same split as
``tools.ml.dataset.types.Annotation``.
"""

from __future__ import annotations

from dataclasses import dataclass

from pod_contracts import BBox


@dataclass(frozen=True, slots=True)
class GroundTruthBox:
    class_id: int
    class_name: str
    bbox: BBox


@dataclass(frozen=True, slots=True)
class PredictedBox:
    class_id: int
    class_name: str
    confidence: float
    bbox: BBox

"""Ground-truth/prediction matching, metrics and deterministic evaluation reports."""

from __future__ import annotations

from .metrics import (
    EvaluationSummary,
    Match,
    MatchResult,
    evaluate_image,
    iou,
    match_detections,
    summarize_matches,
)
from .report import EvaluationReport, ImageEvaluation, build_report
from .types import GroundTruthBox, PredictedBox

__all__ = [
    "EvaluationReport",
    "EvaluationSummary",
    "GroundTruthBox",
    "ImageEvaluation",
    "Match",
    "MatchResult",
    "PredictedBox",
    "build_report",
    "evaluate_image",
    "iou",
    "match_detections",
    "summarize_matches",
]

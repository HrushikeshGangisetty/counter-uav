"""Ground-truth / prediction matching and detection metrics. Deterministic, pure.

``iou_threshold`` is a required argument everywhere it is used, never a default: it
is an evaluation-*methodology* choice (like COCO's 0.5), and this project has not
picked one, so a caller states it explicitly rather than inheriting a silently
"standard" value. The production acceptance metric and threshold are OD-B3 and
separately OPEN --- this module computes precision/recall/IoU, it does not judge
whether a number is good enough.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from pod_contracts import BBox

from .types import GroundTruthBox, PredictedBox


def iou(a: BBox, b: BBox) -> float:
    """Intersection-over-union of two axis-aligned boxes. 0.0 if they do not
    overlap, or if both have zero area."""
    ax2, ay2 = a.x_px + a.w_px, a.y_px + a.h_px
    bx2, by2 = b.x_px + b.w_px, b.y_px + b.h_px
    ix1, iy1 = max(a.x_px, b.x_px), max(a.y_px, b.y_px)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    intersection = iw * ih
    union = a.area_px2() + b.area_px2() - intersection
    if union <= 0:
        return 0.0
    return intersection / union


@dataclass(frozen=True, slots=True)
class Match:
    gt_index: int
    pred_index: int
    iou: float


@dataclass(frozen=True, slots=True)
class MatchResult:
    matches: tuple[Match, ...]
    unmatched_gt: tuple[int, ...]
    unmatched_pred: tuple[int, ...]


def match_detections(
    ground_truth: Sequence[GroundTruthBox],
    predictions: Sequence[PredictedBox],
    *,
    iou_threshold: float,
    class_agnostic: bool = False,
) -> MatchResult:
    """Greedily match predictions to ground truth, highest confidence first.

    For each prediction in descending confidence order, match it to the
    highest-IoU still-unmatched ground-truth box of the same class (or any class if
    ``class_agnostic``) whose IoU is at least ``iou_threshold``. This is the standard
    greedy VOC/COCO-style matching strategy: each ground-truth box matches at most
    one prediction, and a lower-confidence prediction cannot steal a match a
    higher-confidence one already took.
    """
    if not (0.0 <= iou_threshold <= 1.0):
        raise ValueError(f"iou_threshold must be in [0, 1], got {iou_threshold}")

    pred_order = sorted(
        range(len(predictions)), key=lambda i: predictions[i].confidence, reverse=True
    )
    gt_available = set(range(len(ground_truth)))
    matches: list[Match] = []
    unmatched_pred: list[int] = []

    for pred_idx in pred_order:
        pred = predictions[pred_idx]
        best_gt_idx: int | None = None
        best_iou = 0.0
        for gt_idx in gt_available:
            gt = ground_truth[gt_idx]
            if not class_agnostic and gt.class_id != pred.class_id:
                continue
            candidate_iou = iou(gt.bbox, pred.bbox)
            if candidate_iou >= iou_threshold and candidate_iou > best_iou:
                best_iou = candidate_iou
                best_gt_idx = gt_idx
        if best_gt_idx is None:
            unmatched_pred.append(pred_idx)
        else:
            gt_available.discard(best_gt_idx)
            matches.append(Match(gt_index=best_gt_idx, pred_index=pred_idx, iou=best_iou))

    matches.sort(key=lambda m: m.pred_index)
    unmatched_pred.sort()
    unmatched_gt = tuple(sorted(gt_available))
    return MatchResult(
        matches=tuple(matches), unmatched_gt=unmatched_gt, unmatched_pred=tuple(unmatched_pred)
    )


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    """Aggregate counts and rates. ``precision``/``recall``/``mean_iou_matched`` are
    ``None`` when their denominator is zero (undefined), never a fabricated 0.0."""

    num_ground_truth: int
    num_predictions: int
    num_matched: int
    num_false_positives: int
    num_false_negatives: int
    precision: float | None
    recall: float | None
    mean_iou_matched: float | None
    iou_threshold: float


def summarize_matches(
    num_ground_truth: int, num_predictions: int, match: MatchResult, *, iou_threshold: float
) -> EvaluationSummary:
    num_matched = len(match.matches)
    num_fp = len(match.unmatched_pred)
    num_fn = len(match.unmatched_gt)
    precision = num_matched / (num_matched + num_fp) if (num_matched + num_fp) > 0 else None
    recall = num_matched / (num_matched + num_fn) if (num_matched + num_fn) > 0 else None
    mean_iou = statistics.fmean(m.iou for m in match.matches) if match.matches else None
    return EvaluationSummary(
        num_ground_truth=num_ground_truth,
        num_predictions=num_predictions,
        num_matched=num_matched,
        num_false_positives=num_fp,
        num_false_negatives=num_fn,
        precision=precision,
        recall=recall,
        mean_iou_matched=mean_iou,
        iou_threshold=iou_threshold,
    )


def evaluate_image(
    ground_truth: Sequence[GroundTruthBox],
    predictions: Sequence[PredictedBox],
    *,
    iou_threshold: float,
    class_agnostic: bool = False,
) -> tuple[MatchResult, EvaluationSummary]:
    match = match_detections(
        ground_truth, predictions, iou_threshold=iou_threshold, class_agnostic=class_agnostic
    )
    summary = summarize_matches(
        len(ground_truth), len(predictions), match, iou_threshold=iou_threshold
    )
    return match, summary

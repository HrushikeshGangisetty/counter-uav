"""tools.ml.evaluation.metrics: IoU, matching, precision/recall."""

from __future__ import annotations

import pytest

from pod_contracts import BBox
from tools.ml.evaluation.metrics import evaluate_image, iou, match_detections
from tools.ml.evaluation.types import GroundTruthBox, PredictedBox


def _gt(class_id: int, box: tuple[float, float, float, float]) -> GroundTruthBox:
    return GroundTruthBox(class_id=class_id, class_name="uav", bbox=BBox(*box))


def _pred(class_id: int, box: tuple[float, float, float, float], confidence: float) -> PredictedBox:
    return PredictedBox(class_id=class_id, class_name="uav", confidence=confidence, bbox=BBox(*box))


# --- iou -----------------------------------------------------------------------------


def test_iou_identical_boxes_is_one() -> None:
    a = BBox(0.0, 0.0, 10.0, 10.0)
    assert iou(a, a) == pytest.approx(1.0)


def test_iou_no_overlap_is_zero() -> None:
    a = BBox(0.0, 0.0, 10.0, 10.0)
    b = BBox(100.0, 100.0, 10.0, 10.0)
    assert iou(a, b) == 0.0


def test_iou_partial_overlap() -> None:
    a = BBox(0.0, 0.0, 10.0, 10.0)  # area 100
    b = BBox(5.0, 0.0, 10.0, 10.0)  # area 100, overlap [5,10]x[0,10] = 50
    # union = 100+100-50=150
    assert iou(a, b) == pytest.approx(50.0 / 150.0)


def test_iou_zero_area_box_is_zero() -> None:
    a = BBox(0.0, 0.0, 0.0, 0.0)
    b = BBox(0.0, 0.0, 10.0, 10.0)
    assert iou(a, b) == 0.0


# --- match_detections ------------------------------------------------------------


def test_match_detections_perfect_single_match() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    pred = [_pred(0, (0.0, 0.0, 10.0, 10.0), 0.9)]
    result = match_detections(gt, pred, iou_threshold=0.5)
    assert len(result.matches) == 1
    assert result.matches[0].iou == pytest.approx(1.0)
    assert result.unmatched_gt == ()
    assert result.unmatched_pred == ()


def test_match_detections_missed_detection_is_unmatched_gt() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    result = match_detections(gt, [], iou_threshold=0.5)
    assert result.unmatched_gt == (0,)
    assert result.matches == ()


def test_match_detections_false_positive_is_unmatched_pred() -> None:
    pred = [_pred(0, (0.0, 0.0, 10.0, 10.0), 0.9)]
    result = match_detections([], pred, iou_threshold=0.5)
    assert result.unmatched_pred == (0,)
    assert result.matches == ()


def test_match_detections_respects_class_by_default() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    pred = [_pred(1, (0.0, 0.0, 10.0, 10.0), 0.9)]  # different class, perfect overlap
    result = match_detections(gt, pred, iou_threshold=0.5)
    assert result.matches == ()
    assert result.unmatched_gt == (0,)
    assert result.unmatched_pred == (0,)


def test_match_detections_class_agnostic_ignores_class() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    pred = [_pred(1, (0.0, 0.0, 10.0, 10.0), 0.9)]
    result = match_detections(gt, pred, iou_threshold=0.5, class_agnostic=True)
    assert len(result.matches) == 1


def test_match_detections_below_threshold_is_unmatched() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    pred = [_pred(0, (9.0, 0.0, 10.0, 10.0), 0.9)]  # small overlap
    result = match_detections(gt, pred, iou_threshold=0.9)
    assert result.matches == ()


def test_match_detections_higher_confidence_wins_ambiguous_overlap() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    pred = [
        _pred(0, (0.0, 0.0, 10.0, 10.0), 0.4),
        _pred(0, (1.0, 1.0, 10.0, 10.0), 0.95),
    ]
    result = match_detections(gt, pred, iou_threshold=0.1)
    assert len(result.matches) == 1
    assert result.matches[0].pred_index == 1
    assert result.unmatched_pred == (0,)


def test_match_detections_rejects_out_of_range_threshold() -> None:
    with pytest.raises(ValueError):
        match_detections([], [], iou_threshold=1.5)


# --- evaluate_image / summary ------------------------------------------------------


def test_evaluate_image_precision_recall_undefined_when_no_predictions() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    _, summary = evaluate_image(gt, [], iou_threshold=0.5)
    assert summary.precision is None
    assert summary.recall == 0.0
    assert summary.mean_iou_matched is None


def test_evaluate_image_precision_recall_undefined_when_no_ground_truth() -> None:
    pred = [_pred(0, (0.0, 0.0, 10.0, 10.0), 0.9)]
    _, summary = evaluate_image([], pred, iou_threshold=0.5)
    assert summary.recall is None
    assert summary.precision == 0.0


def test_evaluate_image_perfect_detection() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0))]
    pred = [_pred(0, (0.0, 0.0, 10.0, 10.0), 0.9)]
    _, summary = evaluate_image(gt, pred, iou_threshold=0.5)
    assert summary.precision == 1.0
    assert summary.recall == 1.0
    assert summary.num_false_positives == 0
    assert summary.num_false_negatives == 0
    assert summary.mean_iou_matched == pytest.approx(1.0)


def test_evaluate_image_is_deterministic() -> None:
    gt = [_gt(0, (0.0, 0.0, 10.0, 10.0)), _gt(0, (50.0, 50.0, 5.0, 5.0))]
    pred = [_pred(0, (0.0, 0.0, 10.0, 10.0), 0.9), _pred(0, (200.0, 200.0, 5.0, 5.0), 0.7)]
    r1 = evaluate_image(gt, pred, iou_threshold=0.5)
    r2 = evaluate_image(gt, pred, iou_threshold=0.5)
    assert r1 == r2

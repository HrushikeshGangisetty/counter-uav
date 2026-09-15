"""tools.ml.evaluation.report: deterministic aggregate reports."""

from __future__ import annotations

import json

import pytest

from tools.ml.evaluation.metrics import EvaluationSummary
from tools.ml.evaluation.report import ImageEvaluation, build_report


def _summary(**overrides) -> EvaluationSummary:
    base = dict(
        num_ground_truth=1,
        num_predictions=1,
        num_matched=1,
        num_false_positives=0,
        num_false_negatives=0,
        precision=1.0,
        recall=1.0,
        mean_iou_matched=0.8,
        iou_threshold=0.5,
    )
    base.update(overrides)
    return EvaluationSummary(**base)


def test_aggregate_sums_counts_across_images() -> None:
    images = [
        ImageEvaluation("a", _summary(num_matched=1, num_false_positives=1, num_false_negatives=0)),
        ImageEvaluation("b", _summary(num_matched=2, num_false_positives=0, num_false_negatives=1)),
    ]
    report = build_report("ds", "model-1", 0.5, images)
    agg = report.aggregate()
    assert agg.num_matched == 3
    assert agg.num_false_positives == 1
    assert agg.num_false_negatives == 1


def test_aggregate_weighted_mean_iou() -> None:
    images = [
        ImageEvaluation("a", _summary(num_matched=1, mean_iou_matched=1.0)),
        ImageEvaluation("b", _summary(num_matched=3, mean_iou_matched=0.5)),
    ]
    report = build_report("ds", "model-1", 0.5, images)
    # weighted: (1*1.0 + 3*0.5) / 4 = 0.625
    assert report.aggregate().mean_iou_matched == pytest.approx(0.625)


def test_aggregate_precision_recall_none_when_totals_are_zero() -> None:
    images = [
        ImageEvaluation(
            "a",
            _summary(
                num_matched=0,
                num_false_positives=0,
                num_false_negatives=0,
                num_predictions=0,
                num_ground_truth=0,
                precision=None,
                recall=None,
                mean_iou_matched=None,
            ),
        )
    ]
    report = build_report("ds", "model-1", 0.5, images)
    agg = report.aggregate()
    assert agg.precision is None
    assert agg.recall is None
    assert agg.mean_iou_matched is None


def test_to_dict_orders_images_by_sample_id_regardless_of_input_order() -> None:
    images = [ImageEvaluation("z", _summary()), ImageEvaluation("a", _summary())]
    report = build_report("ds", "model-1", 0.5, images)
    ordered_ids = [i["sample_id"] for i in report.to_dict()["images"]]
    assert ordered_ids == ["a", "z"]


def test_to_json_is_deterministic_and_valid_json() -> None:
    images = [ImageEvaluation("a", _summary())]
    report = build_report("ds", "model-1", 0.5, images, generated_at="2026-09-15T00:00:00Z")
    text = report.to_json()
    assert report.to_json() == text
    parsed = json.loads(text)
    assert parsed["generated_at"] == "2026-09-15T00:00:00Z"
    assert parsed["dataset_id"] == "ds"


def test_generated_at_is_never_defaulted_to_a_clock_reading() -> None:
    report = build_report("ds", "model-1", 0.5, [])
    assert report.generated_at == ""

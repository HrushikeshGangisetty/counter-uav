"""Deterministic evaluation reports, serializable for future experiment tracking.

No clock read happens here: ``generated_at`` is a caller-supplied string, exactly the
``CalibrationBundle.created`` convention (``tools/calibration/model.py``) --- the
module records what it is given, it does not manufacture a timestamp.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from .metrics import EvaluationSummary


@dataclass(frozen=True, slots=True)
class ImageEvaluation:
    sample_id: str
    summary: EvaluationSummary


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """One evaluation run: per-image summaries plus their aggregate."""

    dataset_id: str
    model_artifact_id: str
    iou_threshold: float
    images: tuple[ImageEvaluation, ...]
    generated_at: str = ""

    def aggregate(self) -> EvaluationSummary:
        """The overall summary across every image. Precision/recall are
        undefined-safe: a report with zero predictions or zero ground truth overall
        still returns ``None`` rather than a divide-by-zero-shaped fabrication."""
        num_gt = sum(i.summary.num_ground_truth for i in self.images)
        num_pred = sum(i.summary.num_predictions for i in self.images)
        num_matched = sum(i.summary.num_matched for i in self.images)
        num_fp = sum(i.summary.num_false_positives for i in self.images)
        num_fn = sum(i.summary.num_false_negatives for i in self.images)
        precision = num_matched / (num_matched + num_fp) if (num_matched + num_fp) > 0 else None
        recall = num_matched / (num_matched + num_fn) if (num_matched + num_fn) > 0 else None

        # Weighted mean of per-image mean IoU, weighted by each image's match count
        # -- mathematically identical to the mean over every individual match.
        weighted_iou_sum = 0.0
        weighted_iou_count = 0
        for image in self.images:
            if image.summary.mean_iou_matched is not None and image.summary.num_matched > 0:
                weighted_iou_sum += image.summary.mean_iou_matched * image.summary.num_matched
                weighted_iou_count += image.summary.num_matched
        mean_iou = weighted_iou_sum / weighted_iou_count if weighted_iou_count > 0 else None

        return EvaluationSummary(
            num_ground_truth=num_gt,
            num_predictions=num_pred,
            num_matched=num_matched,
            num_false_positives=num_fp,
            num_false_negatives=num_fn,
            precision=precision,
            recall=recall,
            mean_iou_matched=mean_iou,
            iou_threshold=self.iou_threshold,
        )

    def to_dict(self) -> dict[str, object]:
        def summary_dict(s: EvaluationSummary) -> dict[str, object]:
            return {
                "num_ground_truth": s.num_ground_truth,
                "num_predictions": s.num_predictions,
                "num_matched": s.num_matched,
                "num_false_positives": s.num_false_positives,
                "num_false_negatives": s.num_false_negatives,
                "precision": s.precision,
                "recall": s.recall,
                "mean_iou_matched": s.mean_iou_matched,
                "iou_threshold": s.iou_threshold,
            }

        return {
            "dataset_id": self.dataset_id,
            "model_artifact_id": self.model_artifact_id,
            "iou_threshold": self.iou_threshold,
            "generated_at": self.generated_at,
            "aggregate": summary_dict(self.aggregate()),
            "images": [
                {"sample_id": i.sample_id, "summary": summary_dict(i.summary)}
                for i in sorted(self.images, key=lambda i: i.sample_id)
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def build_report(
    dataset_id: str,
    model_artifact_id: str,
    iou_threshold: float,
    images: Sequence[ImageEvaluation],
    *,
    generated_at: str = "",
) -> EvaluationReport:
    return EvaluationReport(
        dataset_id=dataset_id,
        model_artifact_id=model_artifact_id,
        iou_threshold=iou_threshold,
        images=tuple(images),
        generated_at=generated_at,
    )

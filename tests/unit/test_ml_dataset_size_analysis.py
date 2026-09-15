"""tools.ml.dataset.size_analysis: pixels-on-target measurement machinery."""

from __future__ import annotations

import pytest

from pod_contracts import BBox
from tools.ml.dataset.size_analysis import (
    bucket_by_size,
    compute_target_sizes,
    summarize_distribution,
)
from tools.ml.dataset.types import Annotation, DatasetSample


def _sample_with_boxes(
    sample_id: str, boxes: list[tuple[float, float, float, float]]
) -> DatasetSample:
    anns = tuple(Annotation(0, "uav", BBox(*b)) for b in boxes)
    return DatasetSample(sample_id, f"{sample_id}.png", 1000, 500, annotations=anns)


def test_compute_target_sizes_basic() -> None:
    sample = _sample_with_boxes("a", [(0.0, 0.0, 10.0, 20.0)])
    (record,) = compute_target_sizes([sample])
    assert record.width_px == 10.0
    assert record.height_px == 20.0
    assert record.area_px2 == 200.0
    assert record.min_side_px == 10.0
    assert record.area_fraction == pytest.approx(200.0 / (1000 * 500))


def test_compute_target_sizes_one_record_per_annotation() -> None:
    sample = _sample_with_boxes("a", [(0.0, 0.0, 10.0, 10.0), (1.0, 1.0, 5.0, 5.0)])
    records = compute_target_sizes([sample])
    assert len(records) == 2


def test_compute_target_sizes_skips_non_positive_image_dims() -> None:
    sample = DatasetSample(
        "a",
        "a.png",
        0,
        500,
        annotations=(Annotation(0, "uav", BBox(0.0, 0.0, 10.0, 10.0)),),
    )
    assert compute_target_sizes([sample]) == ()


def test_summarize_distribution_empty() -> None:
    summary = summarize_distribution([])
    assert summary.count == 0
    assert summary.minimum is None
    assert summary.mean is None
    assert summary.stdev is None


def test_summarize_distribution_single_value_stdev_is_none() -> None:
    summary = summarize_distribution([5.0])
    assert summary.count == 1
    assert summary.mean == 5.0
    assert summary.stdev is None


def test_summarize_distribution_multiple_values() -> None:
    summary = summarize_distribution([1.0, 2.0, 3.0, 4.0])
    assert summary.count == 4
    assert summary.minimum == 1.0
    assert summary.maximum == 4.0
    assert summary.mean == pytest.approx(2.5)
    assert summary.median == pytest.approx(2.5)
    assert summary.stdev == pytest.approx(1.2909944, rel=1e-5)


def test_bucket_by_size_partitions_by_min_side() -> None:
    sample = _sample_with_boxes(
        "a", [(0.0, 0.0, 5.0, 5.0), (0.0, 0.0, 50.0, 50.0), (0.0, 0.0, 500.0, 500.0)]
    )
    records = compute_target_sizes([sample])
    buckets = bucket_by_size(
        records, {"small": (0.0, 10.0), "medium": (10.0, 100.0), "large": (100.0, 1e9)}
    )
    assert len(buckets["small"]) == 1
    assert len(buckets["medium"]) == 1
    assert len(buckets["large"]) == 1


def test_bucket_by_size_omits_out_of_range_records() -> None:
    sample = _sample_with_boxes("a", [(0.0, 0.0, 500.0, 500.0)])
    records = compute_target_sizes([sample])
    buckets = bucket_by_size(records, {"small": (0.0, 10.0)})
    assert buckets["small"] == ()
    assert sum(len(v) for v in buckets.values()) < len(records)


def test_bucket_by_size_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="key"):
        bucket_by_size((), {"small": (0.0, 1.0)}, key="not_a_field")


def test_bucket_by_size_can_use_area_fraction() -> None:
    sample = _sample_with_boxes("a", [(0.0, 0.0, 100.0, 100.0)])
    records = compute_target_sizes([sample])
    buckets = bucket_by_size(records, {"any": (0.0, 1.0)}, key="area_fraction")
    assert len(buckets["any"]) == 1

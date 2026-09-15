"""Pixels-on-target measurement --- machinery only, no acceptance floor.

[Decision 0014](../../../docs/decisions/0014-public-dataset-training-now.md): the
pixels-on-target floor (OD-B3) "gates the flight-lens decision (OD-19)... get it
empirically: downscale targets progressively and find where recall collapses." That
measurement needs a floor and a downscale/recall experiment neither of which exists
yet; this module only builds the machinery to compute and bucket target sizes once
those exist. No small/medium/large boundary is hard-coded anywhere here.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .types import DatasetSample


@dataclass(frozen=True, slots=True)
class TargetSizeRecord:
    """One annotated box's size, in both pixels and image-relative terms."""

    sample_id: str
    class_id: int
    class_name: str
    width_px: float
    height_px: float
    area_px2: float
    #: min(width_px, height_px) -- the dimension a small/far target is most limited
    #: by, and the natural quantity for a pixels-on-target floor.
    min_side_px: float
    area_fraction: float


def compute_target_sizes(samples: Sequence[DatasetSample]) -> tuple[TargetSizeRecord, ...]:
    """One ``TargetSizeRecord`` per annotation across ``samples``. Skips samples
    with non-positive declared image dimensions (area_fraction would be undefined)."""
    out: list[TargetSizeRecord] = []
    for sample in samples:
        if sample.image_width_px <= 0 or sample.image_height_px <= 0:
            continue
        image_area = float(sample.image_width_px) * float(sample.image_height_px)
        for ann in sample.annotations:
            bbox = ann.bbox
            out.append(
                TargetSizeRecord(
                    sample_id=sample.sample_id,
                    class_id=ann.class_id,
                    class_name=ann.class_name,
                    width_px=bbox.w_px,
                    height_px=bbox.h_px,
                    area_px2=bbox.area_px2(),
                    min_side_px=min(bbox.w_px, bbox.h_px),
                    area_fraction=bbox.area_px2() / image_area,
                )
            )
    return tuple(out)


@dataclass(frozen=True, slots=True)
class DistributionSummary:
    count: int
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None
    stdev: float | None


def summarize_distribution(values: Sequence[float]) -> DistributionSummary:
    """Summary statistics over any size quantity (width_px, min_side_px, ...). All
    fields are ``None`` for an empty input rather than a fabricated 0.0, and
    ``stdev`` is ``None`` below two samples (undefined, not zero)."""
    if not values:
        return DistributionSummary(0, None, None, None, None, None)
    return DistributionSummary(
        count=len(values),
        minimum=min(values),
        maximum=max(values),
        mean=statistics.fmean(values),
        median=statistics.median(values),
        stdev=statistics.stdev(values) if len(values) >= 2 else None,
    )


def bucket_by_size(
    records: Sequence[TargetSizeRecord],
    buckets: Mapping[str, tuple[float, float]],
    *,
    key: str = "min_side_px",
) -> dict[str, tuple[TargetSizeRecord, ...]]:
    """Partition ``records`` into named buckets by a half-open range ``[lo, hi)`` on
    one size field. ``buckets`` boundaries are supplied by the caller --- no
    small/medium/large convention is invented here (OD-B3 is OPEN). ``key`` selects
    which ``TargetSizeRecord`` field to bucket on: ``"min_side_px"``, ``"width_px"``,
    ``"height_px"``, ``"area_px2"`` or ``"area_fraction"``.

    A record outside every bucket's range is silently omitted from all buckets, not
    forced into the nearest one -- the caller can detect this by comparing
    ``sum(len(v) for v in result.values())`` against ``len(records)``.
    """
    valid_keys = {"min_side_px", "width_px", "height_px", "area_px2", "area_fraction"}
    if key not in valid_keys:
        raise ValueError(f"key must be one of {sorted(valid_keys)}, got {key!r}")

    result: dict[str, list[TargetSizeRecord]] = {name: [] for name in buckets}
    for record in records:
        value = getattr(record, key)
        for name, (lo, hi) in buckets.items():
            if lo <= value < hi:
                result[name].append(record)
                break
    return {name: tuple(items) for name, items in result.items()}

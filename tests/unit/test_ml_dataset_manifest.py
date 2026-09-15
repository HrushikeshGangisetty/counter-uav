"""tools.ml.dataset.manifest: manifest generation and deterministic splitting."""

from __future__ import annotations

import pytest

from pod_contracts import BBox
from tools.ml.dataset.manifest import (
    SplitError,
    assign_splits,
    build_manifest,
    load_manifest,
    save_manifest,
)
from tools.ml.dataset.types import Annotation, DatasetSample


def _sample(sample_id: str, n_annotations: int = 0) -> DatasetSample:
    anns = tuple(
        Annotation(0, "uav", BBox(float(i), float(i), 5.0, 5.0)) for i in range(n_annotations)
    )
    return DatasetSample(sample_id, f"{sample_id}.png", 100, 100, annotations=anns, split="train")


# --- manifest ----------------------------------------------------------------------


def test_build_manifest_has_stable_order_independent_of_input_order() -> None:
    a, b, c = _sample("c"), _sample("a"), _sample("b")
    m1 = build_manifest([a, b, c], dataset_id="ds", version="v1")
    m2 = build_manifest([b, c, a], dataset_id="ds", version="v1")
    assert m1.sample_ids() == m2.sample_ids() == ("a", "b", "c")


def test_manifest_to_json_is_byte_deterministic() -> None:
    m = build_manifest([_sample("x", 2), _sample("y")], dataset_id="ds", version="v1")
    assert m.to_json() == m.to_json()


def test_manifest_records_annotation_count() -> None:
    m = build_manifest([_sample("x", 3)], dataset_id="ds", version="v1")
    assert m.entries[0].annotation_count == 3


def test_manifest_split_counts() -> None:
    m = build_manifest([_sample("a"), _sample("b")], dataset_id="ds", version="v1")
    assert m.split_counts() == {"train": 2}


def test_manifest_round_trips_through_disk(tmp_path) -> None:
    m = build_manifest([_sample("a", 1), _sample("b")], dataset_id="ds-v2", version="0.1")
    path = tmp_path / "manifest.json"
    save_manifest(m, path)
    loaded = load_manifest(path)
    assert loaded == m


# --- splitting -----------------------------------------------------------------------


def test_assign_splits_requires_ratios_summing_to_one() -> None:
    with pytest.raises(SplitError):
        assign_splits([_sample("a")], {"train": 0.5, "val": 0.4})


def test_assign_splits_rejects_non_positive_ratio() -> None:
    with pytest.raises(SplitError):
        assign_splits([_sample("a")], {"train": 1.0, "val": 0.0})


def test_assign_splits_rejects_empty_ratios() -> None:
    with pytest.raises(SplitError):
        assign_splits([_sample("a")], {})


def test_assign_splits_is_deterministic_for_a_fixed_seed() -> None:
    samples = [_sample(f"s{i}") for i in range(200)]
    ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
    a = assign_splits(samples, ratios, seed=42)
    b = assign_splits(samples, ratios, seed=42)
    assert [s.split for s in a] == [s.split for s in b]


def test_assign_splits_every_sample_gets_a_named_split() -> None:
    samples = [_sample(f"s{i}") for i in range(50)]
    ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
    out = assign_splits(samples, ratios, seed=0)
    assert all(s.split in ratios for s in out)


def test_assign_splits_roughly_matches_ratios_at_scale() -> None:
    samples = [_sample(f"s{i}") for i in range(5000)]
    ratios = {"train": 0.8, "val": 0.1, "test": 0.1}
    out = assign_splits(samples, ratios, seed=7)
    counts = {name: sum(1 for s in out if s.split == name) for name in ratios}
    for name, ratio in ratios.items():
        assert counts[name] / len(samples) == pytest.approx(ratio, abs=0.03)


def test_assign_splits_stable_when_dataset_grows() -> None:
    """Adding new samples must not reassign existing ones -- that is exactly the
    leakage a re-split would otherwise introduce silently."""
    base = [_sample(f"s{i}") for i in range(100)]
    ratios = {"train": 0.8, "val": 0.2}
    before = {s.sample_id: s.split for s in assign_splits(base, ratios, seed=1)}

    grown = base + [_sample(f"s{i}") for i in range(100, 150)]
    after = {s.sample_id: s.split for s in assign_splits(grown, ratios, seed=1)}

    for sample_id, split in before.items():
        assert after[sample_id] == split


def test_assign_splits_preserves_other_fields() -> None:
    original = _sample("a", n_annotations=2)
    (result,) = assign_splits([original], {"train": 1.0})
    assert result.annotations == original.annotations
    assert result.image_path == original.image_path

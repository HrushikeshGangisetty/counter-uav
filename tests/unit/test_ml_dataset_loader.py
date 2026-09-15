"""tools.ml.dataset.loader: JSONL decode, strict and lenient."""

from __future__ import annotations

import json

import pytest

from tools.ml.dataset.loader import (
    DatasetFormatError,
    iter_dataset_jsonl_lenient,
    load_dataset_jsonl,
    sample_from_dict,
)

_VALID = {
    "sample_id": "img_0001",
    "image_path": "images/img_0001.jpg",
    "image_width_px": 1456,
    "image_height_px": 1088,
    "annotations": [
        {"class_id": 0, "class_name": "uav", "x_px": 10.0, "y_px": 20.0, "w_px": 30.0, "h_px": 15.0}
    ],
    "split": "train",
    "dataset_id": "public-v0",
    "source": "roboflow:example",
}


def test_sample_from_dict_valid() -> None:
    sample = sample_from_dict(_VALID)
    assert sample.sample_id == "img_0001"
    assert len(sample.annotations) == 1
    assert sample.annotations[0].class_name == "uav"
    assert sample.split == "train"


def test_sample_from_dict_empty_annotations_is_a_hard_negative() -> None:
    record = dict(_VALID, annotations=[])
    sample = sample_from_dict(record)
    assert sample.annotations == ()


def test_sample_from_dict_missing_annotations_key_raises() -> None:
    record = {k: v for k, v in _VALID.items() if k != "annotations"}
    with pytest.raises(DatasetFormatError, match="annotations"):
        sample_from_dict(record)


@pytest.mark.parametrize(
    "missing", ["sample_id", "image_path", "image_width_px", "image_height_px"]
)
def test_sample_from_dict_missing_required_field_raises(missing: str) -> None:
    record = {k: v for k, v in _VALID.items() if k != missing}
    with pytest.raises(DatasetFormatError):
        sample_from_dict(record)


def test_sample_from_dict_malformed_annotation_raises() -> None:
    record = dict(
        _VALID, annotations=[{"class_id": 0, "class_name": "uav", "x_px": "not a number"}]
    )
    with pytest.raises(DatasetFormatError):
        sample_from_dict(record)


def test_sample_from_dict_annotations_not_a_list_raises() -> None:
    record = dict(_VALID, annotations={"class_id": 0})
    with pytest.raises(DatasetFormatError, match="must be a list"):
        sample_from_dict(record)


def test_load_dataset_jsonl_round_trip(tmp_path) -> None:
    path = tmp_path / "ds.jsonl"
    path.write_text(
        json.dumps(_VALID) + "\n\n" + json.dumps(dict(_VALID, sample_id="img_0002")) + "\n"
    )
    samples = load_dataset_jsonl(path)
    assert [s.sample_id for s in samples] == ["img_0001", "img_0002"]


def test_load_dataset_jsonl_raises_with_line_number(tmp_path) -> None:
    path = tmp_path / "ds.jsonl"
    path.write_text(json.dumps(_VALID) + "\nnot json\n")
    with pytest.raises(DatasetFormatError, match=r":2:"):
        load_dataset_jsonl(path)


def test_iter_dataset_jsonl_lenient_reports_without_raising(tmp_path) -> None:
    path = tmp_path / "ds.jsonl"
    path.write_text(
        json.dumps(_VALID)
        + "\n"
        + "not json\n"
        + json.dumps({k: v for k, v in _VALID.items() if k != "sample_id"})
        + "\n"
    )
    results = list(iter_dataset_jsonl_lenient(path))
    assert len(results) == 3
    assert results[0] == (1, sample_from_dict(_VALID), None)
    assert results[1][1] is None and results[1][2] is not None
    assert results[2][1] is None and results[2][2] is not None

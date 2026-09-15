"""tools.ml.dataset.validate: deterministic dataset validation."""

from __future__ import annotations

import json
import struct

from pod_contracts import BBox
from tools.ml.dataset.schema import ClassSchema
from tools.ml.dataset.types import Annotation, DatasetSample
from tools.ml.dataset.validate import validate_dataset, validate_dataset_file

CLASSES = ClassSchema(("uav",))
_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _png_bytes(width: int, height: int) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return _PNG_SIG + struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"


def _sample(sample_id: str = "s1", **overrides) -> DatasetSample:
    base = dict(
        sample_id=sample_id,
        image_path=f"{sample_id}.png",
        image_width_px=100,
        image_height_px=100,
        annotations=(Annotation(class_id=0, class_name="uav", bbox=BBox(10.0, 10.0, 20.0, 20.0)),),
        split="train",
    )
    base.update(overrides)
    return DatasetSample(**base)


def _write_image(tmp_path, name: str, width: int = 100, height: int = 100):
    (tmp_path / name).write_bytes(_png_bytes(width, height))


# --- clean dataset --------------------------------------------------------------


def test_valid_dataset_has_no_errors(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    result = validate_dataset([_sample()], CLASSES, image_root=tmp_path)
    assert result.is_valid
    assert result.sample_count == 1


def test_check_images_false_skips_filesystem_access(tmp_path) -> None:
    # No image file written at all -- would fail if check_images touched the fs.
    result = validate_dataset([_sample()], CLASSES, image_root=tmp_path, check_images=False)
    assert result.is_valid


# --- per-field checks -------------------------------------------------------------


def test_missing_image_is_reported(tmp_path) -> None:
    result = validate_dataset([_sample()], CLASSES, image_root=tmp_path)
    codes = result.counts_by_code()
    assert codes.get("missing_image") == 1
    assert not result.is_valid


def test_unreadable_image_is_reported(tmp_path) -> None:
    (tmp_path / "s1.png").write_bytes(_PNG_SIG)  # signature only, no IHDR
    result = validate_dataset([_sample()], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("unreadable_image") == 1


def test_image_dims_mismatch_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "s1.png", width=50, height=50)  # declared is 100x100
    result = validate_dataset([_sample()], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("image_dims_mismatch") == 1


def test_invalid_bbox_dims_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    bad = _sample(annotations=(Annotation(0, "uav", BBox(1.0, 1.0, 0.0, 5.0)),))
    result = validate_dataset([bad], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("invalid_bbox_dims") == 1


def test_invalid_image_dims_is_reported(tmp_path) -> None:
    bad = _sample(image_width_px=0, annotations=())
    result = validate_dataset([bad], CLASSES, image_root=tmp_path, check_images=False)
    assert result.counts_by_code().get("invalid_image_dims") == 1


def test_bbox_out_of_bounds_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    bad = _sample(annotations=(Annotation(0, "uav", BBox(90.0, 90.0, 20.0, 20.0)),))
    result = validate_dataset([bad], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("bbox_out_of_bounds") == 1


def test_negative_bbox_origin_is_out_of_bounds(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    bad = _sample(annotations=(Annotation(0, "uav", BBox(-5.0, 0.0, 20.0, 20.0)),))
    result = validate_dataset([bad], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("bbox_out_of_bounds") == 1


def test_unknown_class_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    bad = _sample(annotations=(Annotation(0, "bird", BBox(1.0, 1.0, 5.0, 5.0)),))
    result = validate_dataset([bad], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("unknown_class") == 1


def test_unknown_class_id_out_of_range_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    bad = _sample(annotations=(Annotation(5, "uav", BBox(1.0, 1.0, 5.0, 5.0)),))
    result = validate_dataset([bad], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("unknown_class") == 1


def test_duplicate_sample_id_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    result = validate_dataset([_sample(), _sample()], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("duplicate_sample_id") == 1


def test_empty_dataset_is_reported() -> None:
    result = validate_dataset([], CLASSES)
    assert result.counts_by_code().get("empty_dataset") == 1
    assert not result.is_valid


def test_empty_split_is_reported_only_when_expected(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    result = validate_dataset(
        [_sample(split="train")], CLASSES, image_root=tmp_path, expected_splits=("train", "val")
    )
    assert result.counts_by_code().get("empty_split") == 1

    result_unchecked = validate_dataset([_sample(split="train")], CLASSES, image_root=tmp_path)
    assert "empty_split" not in result_unchecked.counts_by_code()


# --- leakage -----------------------------------------------------------------------


def test_split_leakage_by_shared_image_path_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "shared.png")
    a = _sample(sample_id="a", image_path="shared.png", split="train")
    b = _sample(sample_id="b", image_path="shared.png", split="val")
    result = validate_dataset([a, b], CLASSES, image_root=tmp_path)
    assert result.counts_by_code().get("split_leakage", 0) >= 1


def test_split_leakage_by_shared_sample_id_is_reported(tmp_path) -> None:
    _write_image(tmp_path, "a.png")
    _write_image(tmp_path, "b.png")
    a = DatasetSample("dup", "a.png", 100, 100, split="train")
    b = DatasetSample("dup", "b.png", 100, 100, split="val")
    result = validate_dataset([a, b], CLASSES, image_root=tmp_path, check_images=False)
    codes = [i.code for i in result.issues if i.sample_id == "dup"]
    assert "split_leakage" in codes


def test_no_leakage_across_disjoint_splits(tmp_path) -> None:
    a = _sample(sample_id="a", split="train")
    b = _sample(sample_id="b", split="val")
    result = validate_dataset([a, b], CLASSES, check_images=False)
    assert "split_leakage" not in result.counts_by_code()


# --- validate_dataset_file (loader + validate together) ---------------------------


def test_validate_dataset_file_missing_annotation_is_malformed_record(tmp_path) -> None:
    _write_image(tmp_path, "s1.png")
    record = {
        "sample_id": "s1",
        "image_path": "s1.png",
        "image_width_px": 100,
        "image_height_px": 100,
        # no "annotations" key at all
    }
    ds_path = tmp_path / "ds.jsonl"
    ds_path.write_text(json.dumps(record) + "\n")
    result = validate_dataset_file(ds_path, CLASSES)
    assert result.counts_by_code().get("malformed_record") == 1
    assert not result.is_valid


def test_validate_dataset_file_image_root_defaults_next_to_manifest(tmp_path) -> None:
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "s1.png").write_bytes(_png_bytes(100, 100))
    record = {
        "sample_id": "s1",
        "image_path": "images/s1.png",
        "image_width_px": 100,
        "image_height_px": 100,
        "annotations": [],
    }
    ds_path = tmp_path / "ds.jsonl"
    ds_path.write_text(json.dumps(record) + "\n")
    result = validate_dataset_file(ds_path, CLASSES)
    assert result.is_valid


def test_result_errors_and_warnings_partition_issues(tmp_path) -> None:
    result = validate_dataset([], CLASSES)
    assert len(result.errors()) == len(result.issues)
    assert result.warnings() == ()

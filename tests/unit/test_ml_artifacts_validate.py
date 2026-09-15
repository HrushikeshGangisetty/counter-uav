"""tools.ml.artifacts.validate: structural validation of ModelArtifactMetadata."""

from __future__ import annotations

import pytest

from pod_contracts import ModelArtifactMetadata, NMSLocation, QuantisationEvidence
from tools.ml.artifacts.validate import (
    ArtifactValidationError,
    hard_problems,
    require_valid,
    validate_artifact_metadata,
    validate_class_names_match,
)
from tools.ml.dataset.schema import ClassSchema


def _valid_metadata(**overrides) -> ModelArtifactMetadata:
    base = dict(
        artifact_path="artifacts/model.hef",
        input_width_px=640,
        input_height_px=640,
        nms_location=NMSLocation.ON_DEVICE,
        class_names=("uav",),
        sustained_fps_aggregate=45.0,
        known_limitations="small-object recall untested below 8px",
        quantisation=None,
    )
    base.update(overrides)
    return ModelArtifactMetadata(**base)


def test_valid_metadata_has_no_hard_problems() -> None:
    assert hard_problems(_valid_metadata()) == []


def test_require_valid_does_not_raise_on_valid_metadata() -> None:
    require_valid(_valid_metadata())


def test_invalid_input_dimensions_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(input_width_px=0))
    assert any("dimensions" in p for p in problems)


def test_negative_input_dimensions_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(input_height_px=-1))
    assert any("dimensions" in p for p in problems)


def test_empty_class_names_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(class_names=()))
    assert any("class_names is empty" in p for p in problems)


def test_duplicate_class_names_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(class_names=("uav", "uav")))
    assert any("duplicates" in p for p in problems)


def test_empty_artifact_path_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(artifact_path=""))
    assert any("artifact_path" in p for p in problems)


def test_empty_known_limitations_is_advisory_only() -> None:
    problems = validate_artifact_metadata(_valid_metadata(known_limitations=""))
    assert any(p.startswith("note:") and "known_limitations" in p for p in problems)
    assert hard_problems(_valid_metadata(known_limitations="")) == []


def test_non_positive_fps_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(sustained_fps_aggregate=0.0))
    assert any("sustained_fps_aggregate" in p for p in problems)


def test_none_fps_is_allowed() -> None:
    assert hard_problems(_valid_metadata(sustained_fps_aggregate=None)) == []


def test_quantisation_missing_metric_name_is_reported() -> None:
    q = QuantisationEvidence(
        metric_name="",
        metric_value_fp32=None,
        metric_value_int8=None,
        test_set_id="held-out-v1",
        small_object_regime_covered=True,
    )
    problems = validate_artifact_metadata(_valid_metadata(quantisation=q))
    assert any("metric_name" in p for p in problems)


def test_quantisation_missing_test_set_id_is_reported() -> None:
    q = QuantisationEvidence(
        metric_name="mAP50",
        metric_value_fp32=0.8,
        metric_value_int8=0.75,
        test_set_id="",
        small_object_regime_covered=True,
    )
    problems = validate_artifact_metadata(_valid_metadata(quantisation=q))
    assert any("test_set_id" in p for p in problems)


def test_valid_quantisation_has_no_problems() -> None:
    q = QuantisationEvidence(
        metric_name="mAP50",
        metric_value_fp32=0.8,
        metric_value_int8=0.74,
        test_set_id="held-out-v1",
        small_object_regime_covered=True,
    )
    assert hard_problems(_valid_metadata(quantisation=q)) == []


# --- checksum format -----------------------------------------------------------------


def test_valid_sha256_is_accepted() -> None:
    metadata = _valid_metadata(sha256="a" * 64)
    assert hard_problems(metadata) == []


def test_wrong_length_sha256_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(sha256="deadbeef"))
    assert any("sha256" in p for p in problems)


def test_non_hex_sha256_is_reported() -> None:
    problems = validate_artifact_metadata(_valid_metadata(sha256="z" * 64))
    assert any("sha256" in p for p in problems)


def test_empty_sha256_is_not_reported() -> None:
    assert hard_problems(_valid_metadata(sha256="")) == []


# --- require_valid --------------------------------------------------------------------


def test_require_valid_raises_on_hard_problems() -> None:
    with pytest.raises(ArtifactValidationError):
        require_valid(_valid_metadata(input_width_px=0))


# --- class mismatch --------------------------------------------------------------------


def test_class_names_match_passes_for_identical_schema() -> None:
    problems = validate_class_names_match(_valid_metadata(), ClassSchema(("uav",)))
    assert problems == []


def test_class_names_mismatch_is_reported() -> None:
    problems = validate_class_names_match(
        _valid_metadata(class_names=("bird",)), ClassSchema(("uav",))
    )
    assert len(problems) == 1
    assert "does not match" in problems[0]


def test_class_names_order_matters() -> None:
    metadata = _valid_metadata(class_names=("uav", "bird"))
    problems = validate_class_names_match(metadata, ClassSchema(("bird", "uav")))
    assert len(problems) == 1

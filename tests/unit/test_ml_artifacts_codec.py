"""tools.ml.artifacts.codec: ModelArtifactMetadata JSON (de)serialization + checksum."""

from __future__ import annotations

import hashlib
import json

import pytest

from pod_contracts import ModelArtifactMetadata, NMSLocation, QuantisationEvidence
from pod_contracts.codec import to_dict
from tools.ml.artifacts.checksum import compute_sha256, verify_sha256
from tools.ml.artifacts.codec import (
    ArtifactFormatError,
    artifact_metadata_from_dict,
    load_manifest,
    save_manifest,
    to_manifest_json,
)


def _metadata(**overrides) -> ModelArtifactMetadata:
    base = dict(
        artifact_path="artifacts/model.hef",
        input_width_px=640,
        input_height_px=640,
        nms_location=NMSLocation.HOST_HAILOFILTER,
        class_names=("uav",),
        sustained_fps_aggregate=40.0,
        known_limitations="untested below 8px",
        quantisation=QuantisationEvidence(
            metric_name="mAP50",
            metric_value_fp32=0.82,
            metric_value_int8=0.77,
            test_set_id="held-out-v1",
            small_object_regime_covered=True,
            notes="int8 loss concentrated under 12px",
        ),
        artifact_version="0.1.0",
        architecture="yolov8n",
        licence="AGPL-3.0",
        sha256="a" * 64,
        extra=(("trained_on", "public-v0"),),
    )
    base.update(overrides)
    return ModelArtifactMetadata(**base)


def test_generic_codec_already_encodes_model_artifact_metadata() -> None:
    d = to_dict(_metadata())
    assert d["nms_location"] == "host_hailofilter"
    assert d["quantisation"]["metric_name"] == "mAP50"
    assert d["extra"] == [["trained_on", "public-v0"]]


def test_decode_round_trips_through_generic_encode() -> None:
    original = _metadata()
    decoded = artifact_metadata_from_dict(to_dict(original))
    assert decoded == original


def test_decode_round_trips_without_quantisation() -> None:
    original = _metadata(quantisation=None)
    decoded = artifact_metadata_from_dict(to_dict(original))
    assert decoded == original


def test_decode_missing_required_field_raises() -> None:
    raw = to_dict(_metadata())
    del raw["artifact_path"]
    with pytest.raises(ArtifactFormatError):
        artifact_metadata_from_dict(raw)


def test_decode_missing_quantisation_field_raises() -> None:
    raw = to_dict(_metadata())
    del raw["quantisation"]["metric_name"]
    with pytest.raises(ArtifactFormatError):
        artifact_metadata_from_dict(raw)


def test_decode_bad_nms_location_raises() -> None:
    raw = to_dict(_metadata())
    raw["nms_location"] = "not_a_real_value"
    with pytest.raises(ArtifactFormatError):
        artifact_metadata_from_dict(raw)


def test_decode_rejects_non_object() -> None:
    with pytest.raises(ArtifactFormatError):
        artifact_metadata_from_dict(["not", "an", "object"])


def test_to_manifest_json_is_valid_deterministic_json() -> None:
    text = to_manifest_json(_metadata())
    assert text == to_manifest_json(_metadata())
    parsed = json.loads(text)
    assert parsed["artifact_path"] == "artifacts/model.hef"


def test_save_and_load_manifest_round_trips(tmp_path) -> None:
    original = _metadata()
    path = tmp_path / "manifest.json"
    save_manifest(original, path)
    loaded = load_manifest(path)
    assert loaded == original


# --- checksum -------------------------------------------------------------------------


def test_compute_sha256_matches_hashlib(tmp_path) -> None:
    path = tmp_path / "artifact.hef"
    path.write_bytes(b"pretend this is a compiled model")
    expected = hashlib.sha256(b"pretend this is a compiled model").hexdigest()
    assert compute_sha256(path) == expected


def test_compute_sha256_streams_large_files(tmp_path) -> None:
    path = tmp_path / "artifact.hef"
    data = b"x" * (3 * 1024 * 1024 + 17)  # spans multiple chunks
    path.write_bytes(data)
    assert compute_sha256(path) == hashlib.sha256(data).hexdigest()


def test_verify_sha256_true_and_false(tmp_path) -> None:
    path = tmp_path / "artifact.hef"
    path.write_bytes(b"model bytes")
    correct = hashlib.sha256(b"model bytes").hexdigest()
    assert verify_sha256(path, correct) is True
    assert verify_sha256(path, "0" * 64) is False


def test_verify_sha256_is_case_insensitive(tmp_path) -> None:
    path = tmp_path / "artifact.hef"
    path.write_bytes(b"model bytes")
    correct = hashlib.sha256(b"model bytes").hexdigest()
    assert verify_sha256(path, correct.upper()) is True

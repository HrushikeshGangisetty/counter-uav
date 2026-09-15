"""JSON (de)serialization for ``pod_contracts.ModelArtifactMetadata``.

Encoding already works with no new code: ``pod_contracts.codec.to_dict`` /
``to_json_line`` are generic over any contract dataclass (they dispatch on
``dataclasses.is_dataclass``), so they already serialize ``ModelArtifactMetadata``
correctly, enums and nested ``QuantisationEvidence`` included. ``to_manifest_json``
below is a thin, readable wrapper around that --- not a new codec.

Decoding (JSON -> ``ModelArtifactMetadata``) has no existing counterpart anywhere in
the repository: nothing in ``src/pod_*`` reads a manifest file yet
(``pod_perception.build_pipeline`` takes a bare ``model_hef_path: str``), so this is
tooling-internal, not a cross-module contract gap. It lives here, not in
``pod_contracts``, on that basis --- see the "before coding" note in this pass's
summary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pod_contracts import ModelArtifactMetadata, NMSLocation, QuantisationEvidence
from pod_contracts.codec import to_dict


class ArtifactFormatError(ValueError):
    """A model artifact manifest record is missing a required field or malformed."""


def _quantisation_from_dict(raw: Any) -> QuantisationEvidence:
    if not isinstance(raw, dict):
        raise ArtifactFormatError(f"quantisation must be an object, got {raw!r}")
    try:
        return QuantisationEvidence(
            metric_name=str(raw["metric_name"]),
            metric_value_fp32=(
                None if raw.get("metric_value_fp32") is None else float(raw["metric_value_fp32"])
            ),
            metric_value_int8=(
                None if raw.get("metric_value_int8") is None else float(raw["metric_value_int8"])
            ),
            test_set_id=str(raw["test_set_id"]),
            small_object_regime_covered=bool(raw["small_object_regime_covered"]),
            notes=str(raw.get("notes", "")),
        )
    except KeyError as exc:
        raise ArtifactFormatError(f"quantisation is missing required field {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ArtifactFormatError(f"quantisation has a malformed field: {exc}") from exc


def artifact_metadata_from_dict(raw: Any) -> ModelArtifactMetadata:
    """Inverse of ``pod_contracts.codec.to_dict`` for ``ModelArtifactMetadata``.
    Raises ``ArtifactFormatError`` on any missing or malformed required field."""
    if not isinstance(raw, dict):
        raise ArtifactFormatError(f"artifact manifest must be an object, got {raw!r}")
    try:
        quant_raw = raw.get("quantisation")
        extra_raw = raw.get("extra", ())
        return ModelArtifactMetadata(
            artifact_path=str(raw["artifact_path"]),
            input_width_px=int(raw["input_width_px"]),
            input_height_px=int(raw["input_height_px"]),
            nms_location=NMSLocation(str(raw["nms_location"])),
            class_names=tuple(str(c) for c in raw["class_names"]),
            sustained_fps_aggregate=(
                None
                if raw.get("sustained_fps_aggregate") is None
                else float(raw["sustained_fps_aggregate"])
            ),
            known_limitations=str(raw["known_limitations"]),
            quantisation=(None if quant_raw is None else _quantisation_from_dict(quant_raw)),
            artifact_version=str(raw.get("artifact_version", "")),
            architecture=str(raw.get("architecture", "")),
            licence=str(raw.get("licence", "")),
            sha256=str(raw.get("sha256", "")),
            extra=tuple((str(k), str(v)) for k, v in extra_raw),
        )
    except KeyError as exc:
        raise ArtifactFormatError(f"artifact manifest is missing required field {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ArtifactFormatError(f"artifact manifest has a malformed field: {exc}") from exc


def to_manifest_json(metadata: ModelArtifactMetadata) -> str:
    """Pretty-printed, deterministic JSON for one artifact manifest file."""
    return json.dumps(to_dict(metadata), indent=2, sort_keys=True) + "\n"


def save_manifest(metadata: ModelArtifactMetadata, path: str | Path) -> None:
    Path(path).write_text(to_manifest_json(metadata), encoding="utf-8", newline="\n")


def load_manifest(path: str | Path) -> ModelArtifactMetadata:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return artifact_metadata_from_dict(data)

"""Structural validation for ``pod_contracts.ModelArtifactMetadata``.

Checks only what a project document supports (``schemas/model_artifact.md``): field
presence, type sanity, positivity of dimensions, no duplicate/empty class names.
There is deliberately no accuracy/acceptance gate here --- ``[Document 2 section
6.2]`` "no acceptance gate is defined for Person A to accept or reject a delivered
model" and ``pod_contracts.MODEL_ACCEPTANCE_GATE`` is literally the string
``"OPEN"``. Integration remains a reviewed human decision; this module only catches
manifests that are structurally broken before a human looks at them.

Mirrors ``tools.calibration.CalibrationBundle``'s ``validate()``/``hard_problems()``
pattern: a ``"note:"``-prefixed line is advisory, everything else blocks acceptance.
"""

from __future__ import annotations

from pod_contracts import ModelArtifactMetadata, QuantisationEvidence

from ..dataset.schema import ClassSchema


class ArtifactValidationError(ValueError):
    """A ``ModelArtifactMetadata`` has a hard structural problem."""


def _is_sha256_hex(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _validate_quantisation(q: QuantisationEvidence) -> list[str]:
    problems: list[str] = []
    if not q.metric_name:
        problems.append(
            "quantisation.metric_name is empty (OD-B3 is OPEN, but an empty name records nothing)"
        )
    if not q.test_set_id:
        problems.append("quantisation.test_set_id is empty")
    return problems


def validate_artifact_metadata(metadata: ModelArtifactMetadata) -> list[str]:
    """Structural problems with ``metadata``. Lines beginning ``"note:"`` are
    advisory; everything else is a hard problem (see ``hard_problems``)."""
    problems: list[str] = []

    if not metadata.artifact_path:
        problems.append("artifact_path is empty")
    if metadata.input_width_px <= 0 or metadata.input_height_px <= 0:
        problems.append(
            f"input dimensions are not positive "
            f"({metadata.input_width_px}x{metadata.input_height_px})"
        )

    if not metadata.class_names:
        problems.append("class_names is empty")
    else:
        if any(not c for c in metadata.class_names):
            problems.append("class_names contains an empty string")
        if len(set(metadata.class_names)) != len(metadata.class_names):
            problems.append(f"class_names has duplicates: {metadata.class_names}")

    if metadata.sustained_fps_aggregate is not None and metadata.sustained_fps_aggregate <= 0:
        problems.append(
            f"sustained_fps_aggregate is not positive ({metadata.sustained_fps_aggregate})"
        )

    if not metadata.known_limitations:
        problems.append(
            "note: known_limitations is empty -- especially small-object behaviour "
            "after quantisation should be stated [schemas/model_artifact.md]"
        )

    if metadata.quantisation is not None:
        problems.extend(_validate_quantisation(metadata.quantisation))

    if metadata.sha256 and not _is_sha256_hex(metadata.sha256):
        problems.append(f"sha256 is not a 64-character hex string: {metadata.sha256!r}")

    return problems


def hard_problems(metadata: ModelArtifactMetadata) -> list[str]:
    """``validate_artifact_metadata`` output with advisory ``"note:"`` lines removed."""
    return [p for p in validate_artifact_metadata(metadata) if not p.startswith("note:")]


def require_valid(metadata: ModelArtifactMetadata) -> None:
    problems = hard_problems(metadata)
    if problems:
        raise ArtifactValidationError("; ".join(problems))


def validate_class_names_match(
    metadata: ModelArtifactMetadata, class_schema: ClassSchema
) -> list[str]:
    """Compare an artifact's declared ``class_names`` (in class_id order) against a
    dataset's ``ClassSchema``. Order matters: ``class_id`` is a position, so a
    reordered list is a real mismatch even with the same set of names."""
    expected = class_schema.class_names
    if tuple(metadata.class_names) != expected:
        return [
            f"artifact class_names {metadata.class_names!r} does not match the "
            f"expected schema {expected!r}"
        ]
    return []

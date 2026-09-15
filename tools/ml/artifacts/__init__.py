"""Validation, checksumming and JSON (de)serialization for a future model artifact
handoff, built on the existing ``pod_contracts.ModelArtifactMetadata`` /
``QuantisationEvidence`` --- no new contract, see this module's docstrings for why.
"""

from __future__ import annotations

from .checksum import compute_sha256, verify_sha256
from .codec import (
    ArtifactFormatError,
    artifact_metadata_from_dict,
    load_manifest,
    save_manifest,
    to_manifest_json,
)
from .validate import (
    ArtifactValidationError,
    hard_problems,
    require_valid,
    validate_artifact_metadata,
    validate_class_names_match,
)

__all__ = [
    "ArtifactFormatError",
    "ArtifactValidationError",
    "artifact_metadata_from_dict",
    "compute_sha256",
    "hard_problems",
    "load_manifest",
    "require_valid",
    "save_manifest",
    "to_manifest_json",
    "validate_artifact_metadata",
    "validate_class_names_match",
    "verify_sha256",
]

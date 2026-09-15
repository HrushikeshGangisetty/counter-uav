"""Dataset representation, validation, manifest/splits and size analysis.

See ``tools/ml/README.md`` for the JSONL interchange format and what remains OPEN.
"""

from __future__ import annotations

from .image_probe import ImageFormat, ImageProbeResult, probe_image
from .loader import (
    DatasetFormatError,
    iter_dataset_jsonl_lenient,
    load_dataset_jsonl,
    sample_from_dict,
)
from .manifest import (
    DatasetManifest,
    ManifestEntry,
    SplitError,
    assign_splits,
    build_manifest,
    load_manifest,
    save_manifest,
)
from .schema import COUNTER_UAV_CLASS_SCHEMA, ClassSchema, ClassSchemaError
from .size_analysis import (
    DistributionSummary,
    TargetSizeRecord,
    bucket_by_size,
    compute_target_sizes,
    summarize_distribution,
)
from .types import Annotation, DatasetSample
from .validate import (
    Severity,
    ValidationIssue,
    ValidationResult,
    validate_dataset,
    validate_dataset_file,
)

__all__ = [
    "COUNTER_UAV_CLASS_SCHEMA",
    "Annotation",
    "ClassSchema",
    "ClassSchemaError",
    "DatasetFormatError",
    "DatasetManifest",
    "DatasetSample",
    "DistributionSummary",
    "ImageFormat",
    "ImageProbeResult",
    "ManifestEntry",
    "Severity",
    "SplitError",
    "TargetSizeRecord",
    "ValidationIssue",
    "ValidationResult",
    "assign_splits",
    "bucket_by_size",
    "build_manifest",
    "compute_target_sizes",
    "iter_dataset_jsonl_lenient",
    "load_dataset_jsonl",
    "load_manifest",
    "probe_image",
    "sample_from_dict",
    "save_manifest",
    "summarize_distribution",
    "validate_dataset",
    "validate_dataset_file",
]

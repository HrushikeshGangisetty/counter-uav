"""Deterministic dataset validation. Structured results, not just printed errors.

Every check is documented below with the exact condition it flags; several of the
task's checks collapse onto the same underlying field and are named separately here
so the mapping is auditable:

    missing image              -> "missing_image"
    unreadable image           -> "unreadable_image" (empty file, or a recognized
                                   PNG/JPEG header that fails to parse)
    invalid bounding boxes /
      zero-negative dimensions -> "invalid_bbox_dims" (w_px <= 0 or h_px <= 0)
    zero/negative image dims   -> "invalid_image_dims"
    coordinates outside bounds -> "bbox_out_of_bounds"
    malformed annotation /
      missing annotation       -> "malformed_record" (from the loader, passed in)
    unknown class               -> "unknown_class"
    duplicate sample ids        -> "duplicate_sample_id"
    image/annotation mismatch   -> "image_dims_mismatch" (declared width/height vs.
                                   the image file's own header, when readable)
    train/val/test leakage      -> "split_leakage"
    empty dataset/split         -> "empty_dataset" / "empty_split"

No I/O happens unless ``check_images=True`` (the default); pass ``False`` for a pure
structural pass over already-loaded samples with no filesystem access.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .image_probe import ImageFormat, probe_image
from .schema import ClassSchema
from .types import DatasetSample


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    severity: Severity
    sample_id: str | None
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...]
    sample_count: int

    @property
    def is_valid(self) -> bool:
        return not any(i.severity is Severity.ERROR for i in self.issues)

    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.WARNING)

    def counts_by_code(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.code] = counts.get(issue.code, 0) + 1
        return counts


def _resolve_image_path(image_path: str, image_root: Path | None) -> Path:
    p = Path(image_path)
    if image_root is not None and not p.is_absolute():
        return image_root / p
    return p


def _validate_sample(
    sample: DatasetSample,
    class_schema: ClassSchema,
    *,
    image_root: Path | None,
    check_images: bool,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    sid = sample.sample_id

    if sample.image_width_px <= 0 or sample.image_height_px <= 0:
        issues.append(
            ValidationIssue(
                "invalid_image_dims",
                Severity.ERROR,
                sid,
                f"declared image size is not positive ({sample.image_width_px}x"
                f"{sample.image_height_px})",
            )
        )

    for ann in sample.annotations:
        bbox = ann.bbox
        if bbox.w_px <= 0 or bbox.h_px <= 0:
            issues.append(
                ValidationIssue(
                    "invalid_bbox_dims",
                    Severity.ERROR,
                    sid,
                    f"bbox has non-positive dimensions (w={bbox.w_px}, h={bbox.h_px})",
                )
            )
        elif sample.image_width_px > 0 and sample.image_height_px > 0:
            x2, y2 = bbox.x_px + bbox.w_px, bbox.y_px + bbox.h_px
            if (
                bbox.x_px < 0
                or bbox.y_px < 0
                or x2 > sample.image_width_px
                or y2 > sample.image_height_px
            ):
                issues.append(
                    ValidationIssue(
                        "bbox_out_of_bounds",
                        Severity.ERROR,
                        sid,
                        f"bbox [{bbox.x_px},{bbox.y_px},{x2},{y2}] is outside the "
                        f"declared image bounds [0,0,{sample.image_width_px},"
                        f"{sample.image_height_px}]",
                    )
                )

        if not class_schema.is_valid(ann.class_id, ann.class_name):
            canonical = class_schema.name_for_id(ann.class_id)
            issues.append(
                ValidationIssue(
                    "unknown_class",
                    Severity.ERROR,
                    sid,
                    f"class_id={ann.class_id} class_name={ann.class_name!r} is not in "
                    f"the schema {class_schema.class_names!r}"
                    + (f" (id maps to {canonical!r})" if canonical else ""),
                )
            )

    if check_images:
        path = _resolve_image_path(sample.image_path, image_root)
        if not path.exists():
            issues.append(
                ValidationIssue("missing_image", Severity.ERROR, sid, f"image not found: {path}")
            )
        else:
            probe = probe_image(path)
            if probe.corrupt:
                issues.append(
                    ValidationIssue(
                        "unreadable_image", Severity.ERROR, sid, f"image is unreadable: {path}"
                    )
                )
            elif (
                probe.format is not ImageFormat.UNKNOWN
                and probe.width_px is not None
                and probe.height_px is not None
                and (probe.width_px, probe.height_px)
                != (sample.image_width_px, sample.image_height_px)
            ):
                issues.append(
                    ValidationIssue(
                        "image_dims_mismatch",
                        Severity.ERROR,
                        sid,
                        f"declared size ({sample.image_width_px}x{sample.image_height_px}) "
                        f"does not match the image file ({probe.width_px}x{probe.height_px})",
                    )
                )

    return issues


def validate_dataset(
    samples: Sequence[DatasetSample],
    class_schema: ClassSchema,
    *,
    parse_issues: Sequence[ValidationIssue] = (),
    image_root: Path | str | None = None,
    check_images: bool = True,
    expected_splits: Sequence[str] = (),
) -> ValidationResult:
    """Validate an already-loaded list of samples.

    ``parse_issues`` lets a caller fold in load-time problems (missing/malformed
    records) from ``dataset.loader.iter_dataset_jsonl_lenient`` so one
    ``ValidationResult`` covers the whole file. ``expected_splits``, if given, makes
    "empty split" checkable for exactly those split names; an unlisted split is never
    flagged as unexpectedly empty (this tool does not invent which splits a dataset
    should have).
    """
    root = Path(image_root) if image_root is not None else None
    issues: list[ValidationIssue] = list(parse_issues)

    seen_ids: Counter[str] = Counter()
    for sample in samples:
        seen_ids[sample.sample_id] += 1
        issues.extend(
            _validate_sample(sample, class_schema, image_root=root, check_images=check_images)
        )

    for sid, count in seen_ids.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    "duplicate_sample_id",
                    Severity.ERROR,
                    sid,
                    f"sample_id {sid!r} appears {count} times",
                )
            )

    issues.extend(_detect_split_leakage(samples))

    if not samples:
        issues.append(
            ValidationIssue("empty_dataset", Severity.ERROR, None, "dataset has no samples")
        )
    else:
        by_split: dict[str, int] = defaultdict(int)
        for sample in samples:
            by_split[sample.split] += 1
        for split in expected_splits:
            if by_split.get(split, 0) == 0:
                issues.append(
                    ValidationIssue(
                        "empty_split", Severity.ERROR, None, f"split {split!r} has no samples"
                    )
                )

    return ValidationResult(issues=tuple(issues), sample_count=len(samples))


def validate_dataset_file(
    path: str | Path,
    class_schema: ClassSchema,
    *,
    image_root: Path | str | None = None,
    check_images: bool = True,
    expected_splits: Sequence[str] = (),
) -> ValidationResult:
    """Load ``path`` (this tool's JSONL format) leniently and validate it in one
    pass. ``image_root`` defaults to the dataset file's own directory, so
    ``image_path`` in each record is relative to where the manifest lives --- the
    same convention ``fixtures/replay`` uses for its JSONL."""
    from .loader import iter_dataset_jsonl_lenient

    samples: list[DatasetSample] = []
    parse_issues: list[ValidationIssue] = []
    for lineno, sample, error in iter_dataset_jsonl_lenient(path):
        if error is not None:
            parse_issues.append(
                ValidationIssue(
                    "malformed_record", Severity.ERROR, None, f"{path}:{lineno}: {error}"
                )
            )
        elif sample is not None:
            samples.append(sample)

    resolved_root = Path(image_root) if image_root is not None else Path(path).resolve().parent
    return validate_dataset(
        samples,
        class_schema,
        parse_issues=parse_issues,
        image_root=resolved_root,
        check_images=check_images,
        expected_splits=expected_splits,
    )


def _detect_split_leakage(samples: Sequence[DatasetSample]) -> list[ValidationIssue]:
    """Flag a sample_id or image_path assigned to more than one distinct split.

    Duplicate sample_ids across splits are also caught here (in addition to
    ``duplicate_sample_id``) because that is precisely how leakage most often enters
    a dataset: the same image exported twice under two split assignments.
    """
    issues: list[ValidationIssue] = []
    splits_by_image: dict[str, set[str]] = defaultdict(set)
    splits_by_id: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        if sample.split:
            splits_by_image[sample.image_path].add(sample.split)
            splits_by_id[sample.sample_id].add(sample.split)

    for image_path, splits in splits_by_image.items():
        if len(splits) > 1:
            issues.append(
                ValidationIssue(
                    "split_leakage",
                    Severity.ERROR,
                    None,
                    f"image {image_path!r} appears in more than one split: {sorted(splits)}",
                )
            )
    for sid, splits in splits_by_id.items():
        if len(splits) > 1:
            issues.append(
                ValidationIssue(
                    "split_leakage",
                    Severity.ERROR,
                    sid,
                    f"sample_id {sid!r} appears in more than one split: {sorted(splits)}",
                )
            )
    return issues

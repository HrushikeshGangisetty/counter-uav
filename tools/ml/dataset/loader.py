"""Load ``DatasetSample`` records from this tool's JSONL interchange format.

One JSON object per line, mirroring ``fixtures/replay/*.jsonl``'s shape (one message
per line, in order) but for dataset samples rather than ``TrackFrame``:

    {"sample_id": "img_0001", "image_path": "images/img_0001.jpg",
     "image_width_px": 1456, "image_height_px": 1088,
     "annotations": [{"class_id": 0, "class_name": "uav",
                       "x_px": 10.0, "y_px": 20.0, "w_px": 30.0, "h_px": 15.0}],
     "split": "train", "dataset_id": "public-v0", "source": "roboflow:example"}

``annotations: []`` is a deliberate hard-negative sample. A record with no
``annotations`` key at all is "missing annotation" and is reported, not guessed.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pod_contracts import BBox

from .types import Annotation, DatasetSample


class DatasetFormatError(ValueError):
    """A dataset record is missing a required field or has the wrong shape."""


def _annotation_from_dict(raw: Any) -> Annotation:
    if not isinstance(raw, dict):
        raise DatasetFormatError(f"annotation must be an object, got {raw!r}")
    try:
        return Annotation(
            class_id=int(raw["class_id"]),
            class_name=str(raw["class_name"]),
            bbox=BBox(
                x_px=float(raw["x_px"]),
                y_px=float(raw["y_px"]),
                w_px=float(raw["w_px"]),
                h_px=float(raw["h_px"]),
            ),
        )
    except KeyError as exc:
        raise DatasetFormatError(f"annotation is missing required field {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise DatasetFormatError(f"annotation has a malformed field: {exc}") from exc


def sample_from_dict(raw: Any) -> DatasetSample:
    """Decode one dataset-sample record. Raises ``DatasetFormatError`` on any missing
    or malformed field --- including an absent ``annotations`` key, which is
    "missing annotation" (distinct from an explicit empty list, a hard negative)."""
    if not isinstance(raw, dict):
        raise DatasetFormatError(f"dataset record must be an object, got {raw!r}")
    try:
        sample_id = str(raw["sample_id"])
        image_path = str(raw["image_path"])
        image_width_px = int(raw["image_width_px"])
        image_height_px = int(raw["image_height_px"])
        annotations_raw = raw["annotations"]
    except KeyError as exc:
        raise DatasetFormatError(
            f"{raw.get('sample_id', '<unknown>')}: missing field {exc}"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise DatasetFormatError(
            f"{raw.get('sample_id', '<unknown>')}: malformed field: {exc}"
        ) from exc

    if not isinstance(annotations_raw, list):
        raise DatasetFormatError(
            f"{sample_id}: 'annotations' must be a list, got {annotations_raw!r}"
        )

    annotations = tuple(_annotation_from_dict(a) for a in annotations_raw)

    return DatasetSample(
        sample_id=sample_id,
        image_path=image_path,
        image_width_px=image_width_px,
        image_height_px=image_height_px,
        annotations=annotations,
        split=str(raw.get("split", "")),
        dataset_id=str(raw.get("dataset_id", "")),
        source=str(raw.get("source", "")),
    )


def load_dataset_jsonl(path: str | Path) -> tuple[DatasetSample, ...]:
    """Strict load: raises ``DatasetFormatError`` on the first malformed line.

    For a pipeline that already trusts its input (e.g. building a manifest from a
    dataset that has already been validated). For reporting every problem in one
    pass, see ``iter_dataset_jsonl_lenient``.
    """
    samples = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetFormatError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            try:
                samples.append(sample_from_dict(raw))
            except DatasetFormatError as exc:
                raise DatasetFormatError(f"{path}:{lineno}: {exc}") from exc
    return tuple(samples)


def iter_dataset_jsonl_lenient(
    path: str | Path,
) -> Iterator[tuple[int, DatasetSample | None, str | None]]:
    """Yield ``(lineno, sample_or_None, error_message_or_None)`` for every non-blank
    line, never raising. Used by ``dataset.validate`` to report every malformed
    record instead of stopping at the first one."""
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                yield (lineno, None, f"invalid JSON: {exc}")
                continue
            try:
                yield (lineno, sample_from_dict(raw), None)
            except DatasetFormatError as exc:
                yield (lineno, None, str(exc))

"""The normalized dataset representation.

Not a CVAT, COCO or YOLO export format --- OD-B2 (dataset spec: size, splits,
scenarios, quality bar, versioning, hard-negative taxonomy) is OPEN, so no final
storage format is assumed. This is this tool's own internal interchange shape;
``tools.ml.dataset.loader`` reads it from JSONL, and an adapter from a real CVAT
export is future work once OD-B2 settles.

Pure: dataclasses only, no I/O, no clock. Reuses ``pod_contracts.BBox`` for bounding
geometry (pixels, top-left origin, x right, y down --- ``docs/contracts.md``) rather
than redefining it, but keeps the annotation/sample wrapper local: this is at-rest
dataset-engineering data, not a cross-module runtime message, the same split
``tools/calibration`` draws between ``CalibrationBundle`` and
``pod_config.CameraIntrinsics`` (decision 0024).
"""

from __future__ import annotations

from dataclasses import dataclass

from pod_contracts import BBox


@dataclass(frozen=True, slots=True)
class Annotation:
    """One ground-truth object box on one image, in sensor/image pixel coordinates."""

    class_id: int
    class_name: str
    bbox: BBox


@dataclass(frozen=True, slots=True)
class DatasetSample:
    """One image and its annotations, normalized.

    ``annotations`` is always a tuple --- possibly empty. An empty tuple is a valid,
    deliberate hard-negative sample, not a missing value; "missing annotation" is a
    property of the raw input record (no annotations key at all), caught at load
    time, not representable here.
    """

    sample_id: str
    image_path: str
    image_width_px: int
    image_height_px: int
    annotations: tuple[Annotation, ...] = ()
    split: str = ""
    dataset_id: str = ""
    source: str = ""

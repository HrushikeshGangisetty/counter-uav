"""tools.ml.dataset.types: the normalized dataset representation."""

from __future__ import annotations

from pod_contracts import BBox
from tools.ml.dataset.types import Annotation, DatasetSample


def test_dataset_sample_defaults() -> None:
    sample = DatasetSample(
        sample_id="s1", image_path="images/s1.jpg", image_width_px=100, image_height_px=100
    )
    assert sample.annotations == ()
    assert sample.split == ""
    assert sample.dataset_id == ""
    assert sample.source == ""


def test_dataset_sample_with_annotations() -> None:
    ann = Annotation(class_id=0, class_name="uav", bbox=BBox(1.0, 2.0, 3.0, 4.0))
    sample = DatasetSample(
        sample_id="s1",
        image_path="images/s1.jpg",
        image_width_px=100,
        image_height_px=100,
        annotations=(ann,),
        split="train",
    )
    assert sample.annotations == (ann,)
    assert sample.annotations[0].bbox.area_px2() == 12.0

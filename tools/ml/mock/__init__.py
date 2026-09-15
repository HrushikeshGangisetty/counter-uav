"""The Detector seam: Frame -> Detector -> Detection[]. See ``detector.py``."""

from __future__ import annotations

from .detector import Detector, MockDetector, constant_detector, single_target_detector

__all__ = ["Detector", "MockDetector", "constant_detector", "single_target_detector"]

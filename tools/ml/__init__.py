"""Person B's ML engineering foundation --- dataset, evaluation and artifact tooling.

Peer of ``tools.camera_bench`` / ``tools.calibration`` (Person C), not a ``src/pod_*``
module. Same rationale as decision 0024: this is dev/build-time tooling with no place
in the seven PRD modules, must stay importable on a laptop with no camera, no Hailo
and no Raspberry Pi, and is therefore never imported by any ``src/pod_*`` module.

Sub-packages:
    dataset      Dataset representation, validation, manifest/splits, class schema,
                 pixels-on-target size analysis.
    evaluation   Ground-truth/prediction matching and metrics, deterministic reports.
    artifacts    Validation and checksumming for ``pod_contracts.ModelArtifactMetadata``.
    mock         A deterministic ``Detector`` seam so Person A/C can exercise
                 downstream perception before a real model or Hailo hardware exists.

Everything here is stdlib-only by design (no numpy/opencv/Pillow): this pass is
pre-dataset infrastructure, not training code, and the project's own dev environment
does not carry the ``vision`` extra. Real image decoding, augmentation and training
are REQUIRES REAL DATA / a later pass --- see ``tools/ml/README.md``.
"""

from __future__ import annotations

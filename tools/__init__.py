"""Developer and bench tooling --- NOT flight software.

``tools/`` is a peer of ``simulation/`` and ``scripts/``: it is never imported by
any ``src/pod_*`` module (``tests/architecture`` forbids that for ``simulation`` and
``tests``; the same intent applies here). It holds the hardware-facing work that has
no place inside the seven PRD modules:

* ``tools.camera_bench`` --- opening the camera, enumerating modes, capturing frames
  and inspecting the result. Depends on ``picamera2`` / ``libcamera``, which are
  platform packages on Raspberry Pi OS and are imported lazily so the package stays
  importable on a laptop.
* ``tools.calibration`` --- the representation, loading and validation of an OpenCV
  intrinsic-calibration result, and its conversion into the
  ``configs/camera/intrinsics_camN.yaml`` shape that ``pod_config`` consumes.

Rationale and the boundary decision: ``docs/decisions/0022``.
"""

from __future__ import annotations

__all__: list[str] = []

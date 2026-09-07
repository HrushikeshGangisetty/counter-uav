"""The perception pipeline, described as data.

Shape from [ARCH Software Stack] and [PRD 2.2]:
    libcamerasrc -> videoconvert -> hailonet -> hailofilter (NMS)
      -> hailotracker (ByteTrack) -> tee
         -> {overlay -> x264enc -> rtspserver}   (video branch, SACRIFICIAL)
         -> {appsink -> Python}                  (control branch)
"""

from __future__ import annotations

from typing import Any

#: A ``Gst.Pipeline``. Typed as Any because ``gi`` is a platform package that is not
#: installed on a developer laptop, and this module must stay importable there.
GstPipeline = Any

#: Ordered element names of the shared trunk, then the two branches.
PIPELINE_ELEMENTS: dict[str, tuple[str, ...]] = {
    "trunk": (
        "libcamerasrc",
        "videoconvert",
        "hailonet",
        "hailofilter",
        "hailotracker",
        "tee",
    ),
    "video_branch": ("queue", "hailooverlay", "videoscale", "x264enc", "rtspserver"),
    "control_branch": ("queue", "appsink"),
}

#: [PRD 5.2] "The appsink feeding the control branch must be configured
#: drop=true max-buffers=1. If Python falls behind we want frames dropped, not
#: queued. A stale frame in a closed loop is worse than no frame."
APPSINK_PROPERTIES: dict[str, object] = {
    "drop": True,
    "max-buffers": 1,
    "emit-signals": True,
    "sync": False,
}

#: [PRD 4.5, 5.5] the video branch is sacrificial: cap at 30 fps regardless of
#: capture rate, downscale before encoding, ultrafast/zerolatency, and it must starve
#: before the control path does. The Pi 5 has no hardware H.264 encoder.
VIDEO_BRANCH_PROPERTIES: dict[str, object] = {
    "speed-preset": "ultrafast",
    "tune": "zerolatency",
    "max_fps": 30,
    "downscale_before_encode": True,
    "sacrificial": True,
}


def describe_pipeline() -> str:
    """Human-readable pipeline shape. No GStreamer needed --- usable off-hardware."""
    trunk = " ! ".join(PIPELINE_ELEMENTS["trunk"])
    video = " ! ".join(PIPELINE_ELEMENTS["video_branch"])
    control = " ! ".join(PIPELINE_ELEMENTS["control_branch"])
    return f"{trunk}\n  tee. ! {video}\n  tee. ! {control}"


def build_pipeline(model_hef_path: str, camera_id: int) -> GstPipeline:
    """Construct the real GStreamer pipeline.

    ⚠ NOT IMPLEMENTED --- M1, Person A. Blocked on hardware (Pi 5, AI HAT+, IMX296)
    and on the device-tree overlay configuration. Do not import ``gi`` at module
    scope: this module must remain importable on a developer laptop with no
    GStreamer installed, which is what lets tests/architecture/ inspect it.
    """
    raise NotImplementedError("pod_perception.build_pipeline: M1 / Person A (hardware-gated)")

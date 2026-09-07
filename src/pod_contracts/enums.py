"""Enumerations shared across pod modules.

Owner: Person A (Hrushikesh). Stdlib only — pod_contracts imports nothing else.
"""

from __future__ import annotations

from enum import Enum


class MissionMode(str, Enum):
    """Mission mode. [PRD 1.2] Selected by operator via RC channel and latched at
    takeoff; NOT runtime-mutable in flight [PRD 1.3 invariant 5]."""

    SURVEILLANCE = "surveillance"
    INTERCEPT = "intercept"


class PodState(str, Enum):
    """The eight states of [ARCH State Machine] (not superseded by PRD v1.1)."""

    IDLE = "IDLE"
    SEARCH = "SEARCH"
    LOCKED = "LOCKED"
    TERMINAL = "TERMINAL"
    BREAKOFF = "BREAKOFF"
    ENGAGE = "ENGAGE"
    LOST = "LOST"
    ABORT = "ABORT"


class CommandDecision(str, Enum):
    """What pod_state tells pod_mavlink to do this tick.

    SILENT is not "send zero velocity". [PRD 4.3]: "on any precondition failure the
    governor must stop sending setpoints, not send zero velocity. Zero velocity is a
    command, and commanding a hover may be exactly wrong."
    """

    SEND = "send"
    SILENT = "silent"


class FlightMode(str, Enum):
    """FC flight mode, as reported over MAVLink. Only GUIDED permits pod influence
    [PRD 1.3 invariant 2]. UNKNOWN is used when the FC mode has not been observed."""

    GUIDED = "GUIDED"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class LatencyStage(str, Enum):
    """The eleven stages of the [PRD 6.2] latency budget, in pipeline order."""

    EXPOSURE = "exposure"
    READOUT_CSI2 = "readout_csi2"
    ISP = "isp"
    PREPROCESS = "preprocess"
    INFERENCE = "inference"
    NMS_DECODE = "nms_decode"
    TRACKER = "tracker"
    APPSINK_TO_PYTHON = "appsink_to_python"
    SELECT_GEOM_GUIDE_FSM = "select_geom_guide_fsm"
    MAVLINK_SERIALISE_UART = "mavlink_serialise_uart"
    FC_INGEST_TO_ATTITUDE = "fc_ingest_to_attitude"


class NMSLocation(str, Enum):
    """Where non-maximum suppression runs. Moves 1-3 ms of CPU load; must be stated
    by Person B with every model artifact [PRD 5.2]."""

    ON_DEVICE = "on_device"
    HOST_HAILOFILTER = "host_hailofilter"
    UNKNOWN = "unknown"


class DistortionModel(str, Enum):
    """Lens distortion model. OD-20 is OPEN: the interim 160 deg fisheye needs
    cv2.fisheye (k1-k4); a telephoto flight lens flips back to pinhole
    (k1,k2,p1,p2,k3). Configurable by requirement, never hard-coded."""

    PINHOLE_RADTAN = "pinhole_radtan"
    FISHEYE_EQUIDISTANT = "fisheye_equidistant"


class RangeMethod(str, Enum):
    """Range-observability method. OD-06 is OPEN; NONE is the only value valid today.
    [PRD 6.1] "Monocular vision cannot observe range."."""

    NONE = "none"
    BBOX_AREA_PROXY = "bbox_area_proxy"
    SIZE_ASSUMED_MONOCULAR = "size_assumed_monocular"
    STEREO_DISPARITY = "stereo_disparity"

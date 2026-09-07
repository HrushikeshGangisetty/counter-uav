"""pod_config --- YAML parameters, camera intrinsics, per-airframe values.

Owner: Person A (Hrushikesh). [PRD 2.3] "Must never import: Anything."

IMPLEMENTATION-0 INTERPRETATION (explicit, see docs/decisions/0016):
this package imports only the standard library, ``yaml`` (a YAML parser is inherent
to a module whose job is YAML parameters) and ``pod_contracts`` (which itself imports
nothing). It imports no other pod_* module and holds no behaviour beyond loading and
validating. tests/architecture/test_import_boundaries.py enforces exactly that.

SAFETY-CRITICAL CONFIGURATION IS BOOT-TIME IMMUTABLE [PRD 7.2, 1.3 invariants 5, 6]:
break-off radius, velocity envelopes and mission mode load from YAML at startup and
cannot be changed from the ground station. Enforced here by (a) frozen dataclasses,
(b) load_pod_config() refusing to run twice in a process without an explicit
reload_for_tests flag.
"""

from __future__ import annotations

from .errors import ConfigError, ConfigOpenError, ConfigReloadError
from .loader import get_pod_config, load_pod_config, reset_for_tests
from .schema import (
    OPEN,
    AirframeConfig,
    CameraIntrinsics,
    MissionConfig,
    PodConfig,
    RCChannelMap,
    SafetyEnvelope,
    is_open,
)

__all__ = [
    "OPEN",
    "AirframeConfig",
    "CameraIntrinsics",
    "ConfigError",
    "ConfigOpenError",
    "ConfigReloadError",
    "MissionConfig",
    "PodConfig",
    "RCChannelMap",
    "SafetyEnvelope",
    "get_pod_config",
    "is_open",
    "load_pod_config",
    "reset_for_tests",
]

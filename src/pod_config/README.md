# pod_config

**Owner:** Person A (Hrushikesh) · **Must never import: Anything** `[PRD 2.3]` — read
as stdlib + `yaml` + `pod_contracts`, per
[decision 0016](../../docs/decisions/0016-pod-config-import-interpretation.md).

YAML parameters, camera intrinsics, per-airframe values. Files live in `configs/`.

**Boot-time immutable** `[PRD 7.2]`: break-off radius, velocity envelopes and mission
mode load once at startup and cannot be changed from the GUI. `load_pod_config()`
refuses a second call in a process; every dataclass is frozen.

**`OPEN` is a sentinel, not a value.** A YAML `OPEN` becomes `pod_config.OPEN`;
`CameraIntrinsics.require_calibrated()` raises `ConfigOpenError` rather than letting
uncalibrated intrinsics produce fabricated geometry (OD-02). `PodConfig.open_fields()`
lists every unmade decision, so a boot log can state them.

**Person C:** your calibration output lands in `configs/camera/intrinsics_cam*.yaml`.
Choose the distortion model first (OD-20).

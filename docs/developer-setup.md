# Developer setup

Everything in this section runs on a laptop with **no pod hardware attached**. That
is deliberate: the pure modules must be testable without hardware `[PRD 4.3]`.

## Requirements

- Python **3.10 or newer**
- git

## Clone, install, verify

```bash
git clone <repo-url> kft-cuav-pod
cd kft-cuav-pod

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m pytest                 # full suite
python -m pytest tests/architecture -v   # boundary enforcement only
python -m ruff check src tests simulation scripts
python -m mypy
```

Or, with make: `make setup && make check`.

Expected result: **all tests pass**, with a group of `xfail`s. Those are not
failures — they are the executable specification for M2 work that has not landed
(see [testing.md](testing.md)).

## Optional extras, installed only when you need them

| Extra | Command | When |
|---|---|---|
| SITL | `pip install -e ".[sitl]"` | M2 — pymavlink, MAVProxy |
| Vision | `pip install -e ".[vision]"` | M2 — NumPy, OpenCV for `pod_geometry` |

## Not pip-installable, by design

**HailoRT**, the **Hailo GStreamer elements**, **libcamera/rpicam-apps** and
**ArduPilot SITL** are platform packages, not Python dependencies. They are documented
rather than wrapped in a setup script, because a hidden installer that half-works on
one laptop is worse than a documented command.

| Dependency | Where | Notes |
|---|---|---|
| Raspberry Pi OS Bookworm 64-bit | The pod | ⚠ **Enable PCIe Gen 3 in `/boot/firmware/config.txt`.** Gen 2 halves accelerator bandwidth and surfaces much later as unexplained inference jitter `[PRD 5.1]` |
| Device-tree overlays | The pod | Two `dtoverlay=imx296,always-on` lines, **exactly one with `,cam0` appended, no space**; external trigger also needs `camera_auto_detect=0` `[PRD 5.1]` |
| HailoRT + PCIe kernel driver | The pod | Vendor runtime; no alternative exists for this accelerator |
| ArduPilot SITL | Dev laptop | See [`simulation/sitl/README.md`](../simulation/sitl/README.md) |

## Where to put your work

| You are | Start in | Read first |
|---|---|---|
| **A — systems & integration** | `src/pod_perception/`, `src/pod_guidance/`, `src/pod_state/`, `src/pod_mavlink/`, `simulation/sitl/` | [architecture.md](architecture.md), [contracts.md](contracts.md) |
| **B — ML & dataset** | [`schemas/model_artifact.md`](../schemas/model_artifact.md) | decisions [0009](decisions/0009-counter-uav-single-class.md), [0013](decisions/0013-yolov8-licence-deferred.md), [0014](decisions/0014-public-dataset-training-now.md) |
| **C — camera & geometry** | `src/pod_geometry/`, `configs/camera/` | decisions [0010](decisions/0010-interim-fisheye-lens.md), [contracts.md](contracts.md) |

Mocks for whatever you do not own yet are in `simulation/mocks.py`, so none of you is
blocked on the others:

```python
from simulation.mocks import make_track_frame, make_vehicle_state, make_rc_state
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `sqlite3.OperationalError: disk I/O error` from mypy | Its cache does not like some network/synced filesystems: `make typecheck MYPY_CACHE_DIR=/tmp/mypy-cache` |
| `ModuleNotFoundError: pod_contracts` | Install the package (`pip install -e ".[dev]"`) — `pyproject.toml` puts `src/` and the repo root on the pytest path, but only inside pytest |
| A test in `tests/architecture` fails | You crossed a module boundary. That is the test doing its job — read the failure message, it cites the PRD clause |

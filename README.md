# KFT Counter-UAV Advisory Pod

Companion-computer software for the KFT / Pavaman Aviation counter-UAV advisory pod:
a self-contained AI payload that looks out through two forward-facing global-shutter
cameras, runs a quantised detector on a Hailo-8L, tracks detections, selects one
track, converts its position in the image into a desired velocity vector, and
**offers** that vector to the host flight controller over MAVLink at 20 Hz.

> The pod advises. It never commands, and never overrides. `[PRD 1.3]`

**Status: Implementation 0 — the development foundation.** Structure, contracts,
configuration, enforcement, tests and documentation. No M1/M2 functionality is
implemented; module entry points raise `NotImplementedError` naming the phase and
owner that will fill them in.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

No hardware required. Full instructions: [docs/developer-setup.md](docs/developer-setup.md).

## Layout

```
src/pod_contracts/   every cross-module dataclass, defined once (stdlib only)
src/pod_config/      YAML parameters, intrinsics, per-airframe values
src/pod_perception/  GStreamer pipeline + appsink callback        (M1)
src/pod_geometry/    undistortion, line-of-sight, range           (M2, pure)
src/pod_guidance/    pursuit and proportional-navigation laws     (M2, pure)
src/pod_state/       state machine, envelope clamps, governor     (M2, pure)
src/pod_mavlink/     the FC serial port — RX, governor, TX        (M2/M3)
src/pod_gcs/         WebSocket telemetry, RTSP video              (M4)
configs/             pod.yaml, airframes/, camera/
schemas/             JSON Schema + the model handoff contract
simulation/          synthetic detections, replay, SITL scaffold, mocks
tools/               camera bench + calibration tooling (Person C, not flight code)
tests/               architecture/ contracts/ unit/ replay/
fixtures/            deterministic replay data
docs/                architecture, contracts, setup, testing, decision log
scripts/             fixture regeneration
```

## Ownership `[Team 2026-09-07]`

| Role | Name | Scope |
|---|---|---|
| A (lead) | **Hrushikesh** | Systems & integration, and the ground station |
| B | **Raghava** | ML & dataset |
| C | **Sreenija** | Camera & vision geometry |

## The rules that do not bend

1. **The FC is the sole authority.** The pod advises.
2. **Go silent, never zero.** On any precondition failure the governor stops sending
   setpoints. Zero velocity is a command, and commanding a hover may be exactly
   wrong.
3. **Exactly one module holds the FC serial handle.** If you want a second writer,
   the answer is no.
4. **Every cross-module message carries a capture timestamp and a frame sequence
   number.**
5. **`pod_geometry`, `pod_guidance`, `pod_state` are pure.** No I/O, no threads, no
   globals.
6. **If a number is not in a document or measured, it is `OPEN`** — and reading it
   raises rather than returning a plausible default.

Rules 3–5 are enforced by `tests/architecture/`, not only by review.

## Read next

| Document | For |
|---|---|
| [CLAUDE.md](CLAUDE.md) | The non-negotiables, for humans and AI assistants alike |
| [docs/architecture.md](docs/architecture.md) | Modules, invariants, data path |
| [docs/contracts.md](docs/contracts.md) | Every message: owner, producer, consumer, units, semantics |
| [docs/decisions/](docs/decisions/) | Why things are the way they are |
| [docs/decisions/open_decisions.md](docs/decisions/open_decisions.md) | **What is still undecided, and who owns it** |
| [docs/developer-setup.md](docs/developer-setup.md) · [testing.md](docs/testing.md) · [contributing.md](docs/contributing.md) | Working here |

## ⚠ Two things to know before you build on this

- **The interim 160° fisheye cannot do counter-UAV.** ~2.6 px on a 0.4 m quad at
  100 m; usable UAV detection range of order 7–16 m. Fine for bring-up, and the
  flight lens (**OD-19**) is the project's highest-priority open decision — itself
  blocked on **OD-U8**, a required detection range that no document has ever stated.
  [decision 0010](docs/decisions/0010-interim-fisheye-lens.md)
- **Hard invariant 7 is not currently satisfied.** The interim Android GCS has a full
  bidirectional MAVLink stack. The exception is written down but **not signed off**.
  [decision 0007](docs/decisions/0007-interim-gcs-invariant-exception.md)

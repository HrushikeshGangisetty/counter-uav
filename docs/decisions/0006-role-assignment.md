# 0006 — Role assignment: A = Hrushikesh, B = Raghava, C = Sreenija

- **Date:** 2026-09-07
- **Status:** CLOSED (OD-U7; resolves the role half of CF-08)
- **Owner:** Team
- **Source:** `[Team 2026-09-07]`

**Decision.**

| Role | Name | Scope |
|---|---|---|
| A (lead) | **Hrushikesh** | Systems & integration — architecture, module interfaces, GStreamer, Hailo, MAVLink, SITL, guidance, state machine, deployment, end-to-end latency, **and the ground station** |
| B | **Raghava** | ML & dataset — dataset, annotation, training, evaluation, quantisation validation, model handoff |
| C | **Sreenija** | Camera & vision geometry — camera and lens, calibration, exposure/gain tuning, undistortion, geometry, line-of-sight, range research |

**Reasoning.** The only prior document mapping people to work
(`day1_kickoff_plan.md`) used an incompatible three-way split with no camera/geometry
owner at all.

**Trade-offs accepted.** Person A now holds six of seven modules, the repository, the
decision log, SITL, the latency harness, deployment, the ground station **and** the
lead role. That is a concentration risk, recorded here so it is visible.

**Alternatives considered.** The `day1_kickoff_plan.md` split (lead/MAVLink, OpenCV,
PyTorch-ML) — leaves camera, lens, calibration and geometry unowned.

**Still open.** **Pod mechanical ownership (OD-U2)** — enclosure, power, wiring,
mounting — has no owner. It blocks the stereo baseline, CF-05 and thermal
remediation.

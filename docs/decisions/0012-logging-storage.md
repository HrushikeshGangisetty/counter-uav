# 0012 — FC logging to SD card; pod-side storage still open

- **Date:** 2026-09-07
- **Status:** PARTIAL — FC side CLOSED, **pod side OPEN as OD-22**
- **Owner:** Person A (Hrushikesh)
- **Source:** `[Team 2026-09-07]`, `[PRD 4.4, 4.6, 4.8]`, Document 4 §1.5

**Decision.** Flight-controller dataflash logging goes to an **SD card on the FC**.
The **pod's own storage is not decided** and is tracked as OD-22.

**Reasoning.** Standard ArduPilot dataflash logging, consistent with the Mission
Planner / QGroundControl log-review workflow and with dataflash+tlog as *"the primary
evidence artifact"* `[PRD 4.6]`.

**Trade-offs accepted.** ⚠ The FC's SD card **does not cover the pod's requirement** —
they are separate machines writing separate things. The Pi 5 separately needs a boot
medium and must write per-stage latency distributions, annotated video, track logs,
replay datasets, and at M5 *"flight logs and imagery that will seed the counter-UAV
dataset workflow"* — image data at volume.

**Alternatives considered (pod side, all still open).** NVMe is **foreclosed**: the
Pi 5's single PCIe lane is consumed by the AI HAT+. That leaves microSD or USB.
Capacity and sustained write throughput for M5 imagery are unquantified.

**Gate.** Needed before M3 logging; **sized** before M5.

# 0003 — Ground station: Kotlin Multiplatform + Compose

- **Date:** August 2026 (PRD v1.1); imported 2026-09-07
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh) `[Team 2026-09-07]`
- **Source:** `[PRD 5.5, 8]`, Document 4 CF-03
- **Supersedes:** the `[ARCH Open Items]` entry "PyQt6 native vs web app — TBD"

**Decision.** One Kotlin Multiplatform + Compose codebase targeting Android tablet
and desktop JVM.

**Reasoning.** Team fluency in Kotlin; an established Kotlin MAVLink library; one
codebase for both a field tablet and a desktop station. *"The ground station is not
in the control loop"* `[PRD 5.5]`, so its latency matters less than its reach.

**Trade-offs accepted.** Compose Multiplatform has no built-in video component, so
the RTSP pane needs a per-platform `expect`/`actual` implementation — *"the single
largest unknown in the ground station"* (OD-13, still open).

**Alternatives considered.** PyQt6 native (lower latency, one platform) and a web app
(faster iteration, weaker field story) — both listed as open in arch v1.0 and both
superseded by an option neither named.

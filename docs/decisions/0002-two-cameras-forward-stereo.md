# 0002 — Camera count: two, forward stereo

- **Date:** August 2026 (PRD v1.1); imported 2026-09-07
- **Status:** CLOSED
- **Owner:** Person A
- **Source:** `[PRD 2.1, 8]`, Document 4 CF-02
- **Supersedes:** the single-camera baseline in `[ARCH Hardware Stack]`

**Decision.** Two forward-facing cameras, hardware-synchronisable via external
trigger.

**Reasoning.** Keeps stereo disparity available as a range-observability option
(OD-06), which monocular vision cannot provide `[PRD 6.1]`.

**Trade-offs accepted.** Three consequences that arch v1.0 was never updated to
reflect and that remain live: the inference budget is **aggregate, not per camera**,
so two cameras means roughly 30–40 FPS each (OD-03); mass roughly doubles on the
camera line (OD-10); and the ±15° adjustable tilt bracket from `[ARCH Mechanical]`
is incompatible with a fixed stereo baseline (**CF-05 / OD-15, still open**).

**Alternatives considered.** One camera, as in arch v1.0 — simpler, lighter, and
forecloses stereo ranging permanently.

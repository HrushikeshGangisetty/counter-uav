# 0001 — Camera sensor: IMX296 global-shutter colour, superseding OV9281 mono

- **Date:** August 2026 (PRD v1.1); imported 2026-09-07
- **Status:** CLOSED
- **Owner:** Person C (Sreenija) for the part; Person A for the system consequence
- **Source:** `[PRD 2.1, 8]`, `[ARCH Hardware Stack]`, Document 4 CF-01
- **Supersedes:** the arch v1.0 selection below

**Decision.** Two Sony IMX296 global-shutter **colour** sensors, 1456×1088 @ 60 fps,
C/CS mount, external-trigger capable. Procured 2026-09-07 as 5 × innomaker units
(2 for the pod, 3 spares).

**Reasoning.** Global shutter is non-negotiable at intercept closing speeds
`[PRD 2.1]`. Colour is mandatory because the dataset is collected on this sensor and
*"any pre-trained monochrome weights are useless"* `[PRD 4.7]`. External trigger is
what makes hardware-synced stereo possible at all.

**Trade-offs accepted.** Heavier and costlier than the mono part: 34 g per body
before glass, against a 250 g pod target (OD-10). Colour costs sensitivity per pixel
in exactly the small-target-against-sky regime that is hardest.

**Alternatives considered.** Arducam OV9281 1 MP global-shutter **mono**, single
unit — the arch v1.0 choice, on the reasoning that *"mono is lighter, cheaper,
sufficient… colour upgradeable later if classification confidence at distance is an
issue."* Rejected once the dataset requirement made colour load-bearing. AR0234
colour GS was considered and rejected in 2026-05.

**Note.** Recorded for traceability precisely because this is the **third** camera
reversal on this project. Do not re-litigate without reading this entry first.

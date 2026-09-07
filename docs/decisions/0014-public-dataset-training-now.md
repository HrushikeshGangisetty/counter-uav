# 0014 — Training starts now, on public datasets, ahead of the custom dataset

- **Date:** 2026-09-07
- **Status:** CLOSED in principle; the programme's detail is OPEN as OD-21
- **Owner:** Person B (Raghava)
- **Source:** `[Team 2026-09-07]`, `[PRD 4.7]`

**Decision.** Phase 1 — train and fine-tune on publicly available UAV datasets,
starting immediately, alongside P0/M1/M2. Phase 2 — fine-tune on KFT-collected data
at M6.

**Reasoning.** The single largest schedule change in the 2026-09-07 revision. It
converts Person B from a role with nothing on the critical path until M5 into one
producing value from day one, and — more importantly — it exercises the Hailo export
chain and INT8 quantisation behaviour **months before they can hurt**. Quantisation
loss in the small-object regime is the project's most predictable nasty surprise, and
this is how it gets found early.

**Trade-offs accepted.** Public UAV imagery does not match the pod's sensor, optics
or operating envelope, so accuracy figures from it are directional, not
acceptance-grade. Time is spent on data that will be superseded. Each source's
licence must be checked before use.

**Alternatives considered.** Wait for the custom dataset at M6 as the PRD sequences
it — leaves the export chain and quantisation behaviour unexercised until the point
of maximum schedule pressure.

**Immediate consequence.** Person B's **pixels-on-target floor (OD-B3)** — how many
pixels a target needs in the model input for reliable detection — is now the most
schedule-critical item on the ML list, because **it gates the flight-lens decision
(OD-19)**, which gates the counter-UAV mission. Get it empirically: downscale targets
progressively and find where recall collapses.

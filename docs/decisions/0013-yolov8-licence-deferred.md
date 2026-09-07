# 0013 — YOLOv8 AGPL-3.0 position deferred, not eliminated

- **Date:** 2026-09-07
- **Status:** DEFERRED (was OD-09) — **re-open before any commercial deployment**
- **Owner:** 🔴 **STILL UNASSIGNED** — legal/commercial, not engineering
- **Source:** `[Team 2026-09-07]`, `[PRD 5.3, 6 item 9]`

**Decision.** Experimentation across architectures proceeds now without settling the
licence question: *"Rn, there is no scope for selling so lets experiment with
different models and see the best ones."* AGPL-3.0 is compatible with internal R&D
use.

**Reasoning.** The PRD's *"resolve this before M6, not during it"* was written
against a commercial-delivery assumption that does not hold today. Blocking
experimentation on a legal question with no current commercial scope costs schedule
for nothing.

**Trade-offs accepted.** ⚠ **The obligation defers; it does not disappear.** AGPL-3.0
attaches at **distribution**, and a pod shipped on a customer airframe is
distribution. The cost of switching architectures rises with every week of
accumulated training work, so the deferral gets more expensive the longer it runs.

**Mitigation.** Person B keeps a **one-line licence note per architecture trialled**,
so the eventual decision is a lookup rather than an archaeology exercise. The
`ModelArtifactMetadata.licence` field exists for exactly this.

**Alternatives considered.** Buy an Ultralytics commercial licence now — spends money
against an unconfirmed commercial plan. Restrict to permissively-licensed
architectures from the start — narrows the search before anything has been measured.

**Re-open trigger.** Any commercial deployment discussion, or the first customer
delivery — whichever comes first.

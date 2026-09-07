# 0011 — Mass budget deferred for prototyping; the ~200 g estimate retired

- **Date:** 2026-09-07
- **Status:** DEFERRED — **re-open before M4 mount** (OD-10)
- **Owner:** Person C (measurement) / Person A (system budget)
- **Source:** `[Team 2026-09-07]`, `[PRD 1.5, 6 item 10]`, `[ARCH Mechanical]`,
  Document 4 §1.11 / CF-06

**Decision.** Mass is deprioritised during prototyping. Working rule: *"compact by
default, add components only where required"*. Separately and permanently: the arch
v1.0 estimate of **"~200 g with margin" is retired. Do not use it.**

**Reasoning.** The 250 g target is a `[PRD 1.5]` **success criterion**, not a
preference — but nothing in bring-up is blocked by mass, and the flight lens (OD-19)
will re-baseline the whole budget anyway. The ~200 g figure was computed against
**one mono camera and no C-mount glass** and is arithmetically stale under the
two-colour-camera baseline; leaving it in place as "the current estimate with margin"
was actively misleading.

**Trade-offs accepted.** Deferring a success criterion changes nothing about whether
it must eventually be met. The interim fisheye is *lighter* than the telephoto the
flight lens will likely require, so the current configuration **flatters** the
budget. CF-06 is closed by retirement, not by a new number — there is currently no
mass estimate at all, which is the honest position.

**Alternatives considered.** Track mass continuously from now — correct in principle,
premature against an enclosure that has no owner (OD-U2) and a lens that has no
specification (OD-19).

**Re-open trigger.** Before the M4 mount (mass and CG are an M4 activity), and
immediately when OD-19 closes.

# 0009 — Counter-UAV taxonomy: single class `uav`, plus sky hard negatives

- **Date:** 2026-09-07
- **Status:** CLOSED for the class list; **taxonomy of hard negatives still OPEN**
- **Owner:** Person B (Raghava)
- **Source:** `[Team 2026-09-07]`, `[PRD 1.3, 4.7]`

**Decision.** One class, `uav`. No size, type or friend/foe subdivision. Non-UAV
airborne and sky-clutter objects are trained as **hard negatives**; the exact
negative taxonomy is finalised during dataset design (OD-B2) and is **not** closed
here.

**Reasoning.** A single class maximises positive examples per class, which matters
most in the small-object regime, and avoids asking annotators to make a type call on
a three-pixel target they cannot actually see. Explicitly training against birds and
other sky clutter was absent from every source document and is a genuine addition.

**Trade-offs accepted.** ⚠ **The model cannot distinguish a hostile UAV from a
friendly one.** Any friend/foe discrimination must therefore come from **outside the
detector** — the RC-triggered operator lock, per hard invariant 4 `[PRD 1.3]`. Stated
explicitly here rather than assumed.

**Alternatives considered.** Multi-class by airframe type or by size — richer
telemetry, far fewer examples per class, and unannotatable at the ranges that matter.

**Surveillance mode is unaffected:** COCO classes 0 person, 2 car, 3 motorcycle,
5 bus, 7 truck `[ARCH Models]`.

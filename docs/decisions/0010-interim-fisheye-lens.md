# 0010 — ⚠ INTERIM: the bundled 160° fisheye is the bring-up lens

- **Date:** 2026-09-07
- **Status:** **INTERIM — expires before M4, hard gate before M6**
- **Owner:** Person C (Sreenija)
- **Source:** `[Team 2026-09-07]`, `[PRD 2.1, 4.1, 6 item 1]`, Document 4 §1.4 / CF-11

**Decision.** Use the 160° fisheye bundled with the innomaker IMX296 units as the
**interim** optic. No separate lenses procured yet. The flight lens is **OD-19**,
which is now the project's highest-priority open decision.

**Reasoning.** Zero cost, zero lead time, already in hand. Everything P0/M1/M2 need
is testable on it: sensor enumeration, sustained frame rate, global-shutter behaviour
under motion, exposure and gain control, thermal stability, driver reliability,
dual-camera enumeration, pipeline throughput, the calibration workflow, LOS maths,
SITL integration. **None of those depend on focal length.**

**Trade-offs accepted — and this is the consequential part.** Computed against the
stated sensor geometry (3.45 µm pitch, 1456×1088, 160° diagonal equidistant):
approximately **2.6 px on a 0.4 m quad at 100 m natively, ~1.1 px after letterboxing
to 640**, giving a usable UAV detection range of roughly **7 m letterboxed / 16 m
native centre-crop**. The PRD's already-pessimistic baseline was 3–8 px `[PRD 6 item
1]`. At 150 m/s closure, 85 ms of pipeline latency is already 12.75 m of travel — a
detection range comparable to the distance the target covers during the pipeline's
own latency is not an engagement envelope.

So, explicitly: **this configuration is fine for bring-up and cannot do counter-UAV
at any useful range.** These figures are **computed, not measured** — `[PRD 4.1]`
requires Person C to measure them, and this entry is the prediction that measurement
should confirm or refute (including whether the vendor's 160° is diagonal or
horizontal; if horizontal, every number is ~20% worse).

Consequences that follow and are recorded elsewhere: stereo disparity ranging is
**effectively suspended** (OD-06) — disparity against a 2.6 px target through a
fisheye is not a range solution; the distortion model must be `cv2.fisheye`, not
radial-tangential, and must be **configuration, not a hard-coded call**, because a
telephoto flight lens flips it back (OD-20); the OD-04 letterbox-vs-crop decision can
have its **mechanism and ratio** measured on this lens but **not its operational
call**, which does not transfer to a telephoto.

**Alternatives considered.** Wait for a specified flight lens before any bring-up —
blocks P0/M1/M2 on a procurement decision that is itself blocked on OD-U8, a range
requirement no document has ever stated. Buy a candidate telephoto now — premature
against an unstated requirement, and Indian-market lead times have already cost this
project three times.

**Expiry.** Before M4 tethered flight; **hard gate before M6**. Intrinsics must be
**recalibrated** when the flight lens lands — intrinsics belong to the camera *and*
lens together.

# 0007 — ⚠ PROPOSED: interim Android GCS, and the receive-only invariant it breaks

- **Date:** 2026-09-07
- **Status:** **PROPOSED — NOT AGREED. Requires sign-off before it counts.**
- **Owner:** Person A (Hrushikesh)
- **Source:** `[Team 2026-09-07]`, `[PRD 1.3, 2.4, 6 item 14]`, Document 4 CF-12 / OD-14

**This entry weakens a hard invariant.** `[PRD 1.3]`: *"Any change that weakens one of
these requires a decision-log entry **and sign-off**."* The entry now exists. **The
sign-off does not.** Until a named person signs this off, the exception is not
accepted — it is merely written down.

**Proposed decision.** Use the existing KFT Android GCS as the interim ground station
until the pod GCS is built, accepting that hard invariant 7 is not satisfied while it
is in use, **with an expiry**:

| Phase | Stance |
|---|---|
| M2 / M3 (bench, props off) | **Accept** the exception |
| M4 (tethered flight) | **Receive-only enforcement required in code** |
| M5 (free flight) | **Hard gate** — no free flight without it |

**Reasoning.** It removes OD-13 (the Compose RTSP video pane) from the near-term
critical path, and the existing app is already Kotlin/Compose — the same stack, not a
detour. Person A gets FC telemetry and a working UI for free during bench work.

**Trade-offs accepted.** An existing production GCS has a full bidirectional MAVLink
stack — arming, mode changes and mission upload are what it is *for*. `[PRD 2.4]`
requires the GCS's FC link to be *"receive-only, enforced in code rather than by
convention"*, because *"the invariant that exactly one module commands the flight
controller was written assuming the ground station could not do this."* **While the
interim GCS is in use, that assumption is false.** The mitigations are procedural
only: props off, a known operator, a pilot on the sticks, and the FC still holding
ultimate authority.

**Alternatives considered.** (a) Build receive-only enforcement into the interim app
first — safest, but pulls the GCS onto the critical path immediately. (b) Use
MAVProxy/QGroundControl read-only for bench work — no custom code, but no pod
telemetry pane. (c) No ground station until M4 — flies blind through M3.

**Sign-off required from:** _______________  **Date:** _______________

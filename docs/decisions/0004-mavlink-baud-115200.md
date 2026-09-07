# 0004 — MAVLink baud rate fixed at 115200

- **Date:** 2026-09-07
- **Status:** CLOSED — but explicitly **reversible**; see the trigger below
- **Owner:** Person A (Hrushikesh)
- **Source:** `[Team 2026-09-07]`, `[ARCH Comms protocols]`, `[PRD 4.4, 5.4, 6.2]`,
  Document 4 CF-04 / OD-07

**Decision.** 115200 baud on the isolated UART to the flight controller. The PRD's
*"raise the baud rate to 921600"* `[PRD 4.4]` is **not** adopted.

**Reasoning.** It matches the existing KFT flight-controller configuration and
removes a variable from bring-up. The `[PRD 6.2]` latency budget was computed at
115200 (MAVLink serialise + UART ~1 ms typical, **6 ms worst case**) and therefore
stands as written.

**Trade-offs accepted.** Three, and they bind:
1. `SRx_*` stream-rate trimming is now **the mitigation, not an optimisation** — at
   921600 there is bandwidth headroom to be sloppy; at 115200 there is not. Trim to
   HEARTBEAT, ATTITUDE, LOCAL_POSITION_NED, RC_CHANNELS, VFR_HUD `[PRD 5.4]`. The
   rate **values** stay OPEN (OD-07b), tuned at M3 from measured link utilisation.
2. A congestion spike of 50–200 ms eats the entire budget on its own (typical total
   55–85 ms against a <200 ms p95 target). `[PRD 4.4]` warns it *"looks exactly like
   an inference stall"* — so the **M3 debugging order is link first, perception
   second.**
3. This is fixed by **choice**, not constraint.

**Alternatives considered.** 921600 as the PRD directs — more headroom, but it
invalidates the published latency budget and changes the FC configuration before
anything has been measured.

**Reversal trigger.** If the M3 measured latency distribution shows link-induced
spikes, raising the baud is the cheapest available fix. Reopen with a new entry.

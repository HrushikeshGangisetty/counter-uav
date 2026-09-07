# pod_guidance

**Owner:** Person A (Hrushikesh) · **Must never import:** GStreamer, pymavlink
`[PRD 2.3]` · **PURE**.

`GuidanceInput` → `VelocityCommand` (body-frame vx, vy, vz, yaw_rate).

**The design requirement that applies from day one** `[PRD 6.1]`: proportional
navigation must sit **behind the same interface** as the pursuit law, so switching is
a configuration change rather than a rewrite — even though PN is not needed until M6.
That is what `LAWS` and `get_law(name)` are for. Adding a law means adding a registry
entry, never an `if` in the control loop.

- **Pursuit** — centres the target in frame. Adequate for surveillance; the law used
  M1–M5. A tail chase: against a crossing target you arrive late and arc in behind.
- **Proportional navigation** — M6, and blocked on **OD-06**: it needs closing
  velocity, which needs range rate, which monocular vision cannot observe.

Emitting a command is not sending one. `pod_state` and the governor decide that.

# 0008 — Detection message schema v1.0 frozen (closes OD-17 / CF-10)

- **Date:** 2026-09-07 (Implementation 0)
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 2.3, 7.2]`, `[DAY1 0]`, Document 4 CF-10 / OD-17
- **Supersedes:** the `[DAY1 0]` draft schema

**Decision.** The perception→control seam is `pod_contracts.TrackFrame`, carrying a
`FrameMeta` (`camera_id`, `frame_seq`, `capture_ts_ns`, `width_px`, `height_px`) and
a tuple of `TrackedObject`. Version 1.0, frozen. See `docs/contracts.md`.

**Reasoning.** The `[DAY1 0]` draft — `{track_id, class, bbox, confidence,
frame_ts}` — carries a timestamp but **no frame sequence number**, and is therefore
non-compliant with a rule `[PRD]` states twice: *"Every cross-module message carries
the capture timestamp and frame sequence number, so any consumer can independently
reject stale data rather than trusting its producer."* This was the first thing that
had to be fixed, because nothing else can be coded against a moving seam.

**Trade-offs accepted.** The schema is more verbose than the draft: the stamp lives
in a nested `frame` object rather than a flat field, which costs a level of JSON
nesting on the wire and one extra line in the Kotlin mirror. Accepted because it
makes the stamp a single unit that cannot be partially copied. `capture_ts_ns` is
**integer nanoseconds on CLOCK_MONOTONIC** — not float seconds, which lose resolution
well inside the latency budget, and not wall-clock, which can step.

**Alternatives considered.** (a) Flat fields on every message — fewer keys, but the
pair gets split and half-copied. `TelemetryFrame` uses the flat form deliberately,
because its wire shape is consumed by a separate language. (b) Adding only the
sequence number to the day-1 draft — smaller change, but leaves units and clock
semantics undocumented, which is how the *next* ambiguity gets in.

**Enforcement.** `tests/contracts/test_message_stamps.py` walks
`pod_contracts.CROSS_MODULE_MESSAGES` and fails any message that carries neither a
`FrameMeta` nor a flat `(capture_ts_ns, frame_seq)` pair. The JSONL decoder rejects
records missing either field, so a non-compliant producer cannot get data in.

# pod_gcs

**Owner:** Person A (Hrushikesh) `[Team 2026-09-07]` · **Must never import:**
pymavlink `[PRD 2.3]`.

The **pod-side** server: WebSocket telemetry out at ~10 Hz, RTSP video, read-only
state view. The Kotlin Multiplatform client application is a separate codebase.

## Two links, deliberately `[PRD 2.4]`

| Link | Carries | Why separate |
|---|---|---|
| FC telemetry radio → GCS | attitude, position, mode, armed, RC channels | Must survive pod death — relaying it through the pod would blind the operator at the worst moment |
| Pod → GCS | tracks, lock state, transitions, per-stage latency, video | No natural home in the standard MAVLink message set |

The pymavlink import ban is the pod-side half of that. Collapsing the links breaks a
hard invariant.

## The command surface stays narrow `[PRD 5.5]`

`lock`, `unlock`, pre-takeoff `mode_set`. Nothing else. *"It must not be able to
change break-off radius, velocity envelopes or mission mode in flight, and it must not
be able to bypass the safety governor."* Unknown commands are rejected, not ignored.

⚠ **CF-12 / OD-14 open:** the interim ground station is the existing KFT Android GCS,
which has a full bidirectional MAVLink stack, so the receive-only requirement backing
invariant 7 is **not met while it is in use**. The exception is written down and
**not yet signed off** —
[decision 0007](../../docs/decisions/0007-interim-gcs-invariant-exception.md).

⚠ Glass-to-glass video latency is tracked **separately** from the control budget
(~300 ms target) `[PRD 6.3]`.

**Status:** M4. OD-13 (the Compose RTSP pane) is deferred by the interim GCS, not
solved.

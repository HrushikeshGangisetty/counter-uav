# 0021 — `pod_mavlink` implementation slice: what's pure, what's lazy, what's deferred

- **Date:** 2026-09-07
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 1.3 invariant 7, 4.3, 5.4, 7.2]`, `docs/contracts.md`

**Decision.** Three structural choices, made together as one slice:

1. **`pod_mavlink` is split into `setpoint.py` (outbound field-building, pure),
   `rx.py` (inbound VehicleState/RCState builders, pure) and `link.py`
   (`MavlinkLink`, the actual serial handle).** The pure halves take and return plain
   values/dataclasses — no pymavlink message objects — so they're testable with
   synthetic data on any machine, matching every other test in this repo
   (`docs/testing.md`: "no test reads a clock, the network, or hardware").
2. **`pymavlink` is imported lazily, inside `MavlinkLink.open()`, not at module
   level.** `pymavlink` is the `sitl` extra (`pyproject.toml`), not a `dev`
   dependency; a top-level import would make `import pod_mavlink` itself require
   hardware-adjacent tooling that `README.md`'s quick start explicitly does not
   install. `MavlinkLink._conn` is a plain (not name-mangled) attribute so tests can
   inject a fake connection double without pymavlink present.
3. **`MavlinkLink.send()` does not call `pod_state.govern()` itself.** `StateOutput`
   is documented as the hand-off point between `pod_state` (producer) and
   `pod_mavlink` (consumer) (`docs/contracts.md` registry). `send()` only inspects
   `output.decision`/`output.command`; it never transmits unless `decision is SEND`
   and `command is not None`, which holds regardless of whether the caller actually
   ran `govern()` first. The integration between the two is verified at the boundary,
   in `tests/unit/test_pod_mavlink_governor_integration.py`, rather than by importing
   `pod_state` from `pod_mavlink`.

Also, not a structural choice but worth recording: `MavlinkLink.send()` requires
`target_system`/`target_component` from the caller, with no default. No project
document assigns MAVLink system/component addressing; a conventional-looking `1`
would be exactly the kind of plausible, unmeasured default the house rule forbids.

**Reasoning.** `MAV_FRAME_BODY_NED = 8` and the `POSITION_TARGET_TYPEMASK` ignore-bit
values in `setpoint.py` are MAVLink `common.xml` protocol constants — fixed by the
wire format, not a project decision — so hard-coding them is implementing a spec, not
inventing a number. `SETPOINT_TYPE_MASK` is computed from the existing
`SETPOINT_TYPE_MASK_FIELDS` tuple rather than hand-written as a literal, so the mask
can never drift from what the README already states is enabled.

**Trade-offs accepted.** `MavlinkLink` cannot be exercised end-to-end without either a
real serial device or the `sitl` extra installed — this slice proves the encode/
decode logic and the SILENT-means-nothing-transmitted invariant, not a live link. The
RX thread itself, the 20 Hz scheduler that calls `send()` on a cadence
(`COMMAND_PERIOD_S` is defined but nothing runs it yet), and the M3 watchdog ("a live
process with a dead control thread is the dangerous case" [PRD 5.5]) are explicitly
not built — they all need a running process and a live port to thread against, which
is SITL/M3 integration work.

**Alternatives considered.**
(a) Import pymavlink at module level and mark the whole test file `skipif` when it's
absent — rejected: it would make `pod_mavlink`'s pure logic (the setpoint encoding,
the RX field builders) untestable on a laptop with no hardware, contradicting the
project's own testing philosophy.
(b) Have `send()` call `pod_state.govern()` internally — rejected per the contracts
registry: `StateOutput` is the documented hand-off; a direct call would make
`pod_mavlink` depend on `pod_state`'s internals for no benefit, since `send()`'s own
SILENT-means-nothing check already gives the same safety property regardless.
(c) Default `target_system`/`target_component` to `1` — rejected; not stated in any
document, and defaulting it would hide that gap instead of surfacing it at the call
site.

**Still open (unchanged by this slice).** OD-07b (`SRx_*` stream-rate values),
`docs/decisions/0004` (baud rate, already CLOSED but reversible). Nothing in this
slice touches either.

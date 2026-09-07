# 0016 — Reading "pod_config must never import anything"

- **Date:** 2026-09-07 (Implementation 0)
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 2.3]`

**Decision.** `[PRD 2.3]` gives `pod_config`'s ban list as **"Anything"**. Taken
literally that forbids a YAML parser, which forbids the module doing its stated job.
The enforced interpretation is: `pod_config` may import **the standard library,
`yaml`, and `pod_contracts`** — and no other `pod_*` module, no GStreamer, no
pymavlink, no serial.

**⚠ This is an interpretation of a PRD rule and is called out as such.**

**Reasoning.** `pod_config` *"owns YAML parameters, camera intrinsics, per-airframe
values"* `[PRD 2.3]`, so a YAML parser is inherent to its job rather than a
dependency it chose. `pod_contracts` imports nothing, so depending on it cannot
create a cycle or drag in a banned package; it is needed for shared enum types
(`MissionMode`, `DistortionModel`) which would otherwise have to be duplicated —
exactly what decision 0015 forbids. The rule's evident intent is that configuration
depends on no *subsystem*, so that every module can safely depend on it.

**Trade-offs accepted.** A documented reading of a PRD rule is weaker than the rule
as written. Mitigated by making it the narrowest possible reading and enforcing it as
an **allowlist** — anything not named fails the test — rather than as a ban list.

**Alternatives considered.** (a) Hand-roll a parser inside `pod_config` to keep the
literal reading — more code, more bugs, no benefit. (b) Put loading in a separate
module and leave `pod_config` as pure schema — splits ownership of one concern across
two modules and invents a ninth package to avoid a documented interpretation.

**Related.** `pod_geometry`, `pod_guidance` and `pod_state` may import `pod_config`
and `pod_contracts` only. That does not breach their purity: the ban is on
*performing* I/O, which the purity tests check directly, not on naming a type whose
package can also load a file.

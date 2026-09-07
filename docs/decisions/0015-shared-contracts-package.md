# 0015 — Shared contracts live in one package, `pod_contracts`

- **Date:** 2026-09-07 (Implementation 0)
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 2.3, 7.2]`, `[DAY1 0]`

**Decision.** Every cross-module data structure is defined exactly once, in
`src/pod_contracts/`. It is stdlib-only, imports no `pod_*` module, and contains no
behaviour — only frozen dataclasses, enums and a JSON codec.

**⚠ This is an architectural addition and is called out as such.** `[PRD 2.3]` names
**seven** modules. `pod_contracts` is an **eighth Python package** but not an eighth
architectural module: it owns no resource, runs no logic and has no lifecycle. The
seven PRD modules and their import bans are unchanged.

**Reasoning.** The PRD requires modules to *"communicate only through plain
dataclasses"* and requires every cross-module message to carry a stamp, but says
nothing about **where those dataclasses live**. Something had to answer that before
three people write code in parallel. `[DAY1 0]` had already reached for the same
answer with a `/protocol` directory for "shared schemas/config"; this is that
directory, renamed to the `pod_*` convention. Because it imports nothing, no module's
`[PRD 2.3]` ban list can be violated by depending on it.

**Trade-offs accepted.** An eighth package to explain to every new reader — mitigated
by this entry and by `docs/contracts.md`. A change to a contract now touches one file
that everyone imports, so contract changes need review from all three owners rather
than one. Accepted: that is the point.

**Alternatives considered.** (a) Define each structure in its producing module and
import across — makes `pod_geometry` import `pod_perception`, which inverts the
dependency the PRD's boundaries are designed to prevent. (b) Duplicate structures per
module and convert at the seams — guarantees the drift `[PRD 5.5]` warns about for the
Python/Kotlin mirror, and here with no compiler to catch it. (c) Put them in
`pod_config` — conflates parameters with messages, and `pod_config` must import
nothing.

**Enforcement.** `tests/contracts/test_no_duplicate_definitions.py` fails if any
contract class is defined outside `pod_contracts`.

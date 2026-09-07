# 0017 — The module boundaries are enforced by tests, not only by review

- **Date:** 2026-09-07 (Implementation 0)
- **Status:** CLOSED
- **Owner:** Person A (Hrushikesh)
- **Source:** `[PRD 2.3, 7.2, 1.3 invariant 7]`

**Decision.** Every boundary rule in `[PRD 2.3]` and `[PRD 7.2]` is expressed as data
in `tests/architecture/rules.py` and checked by AST inspection of `src/`, in CI, as
its own CI step. This covers: per-module import bans, allowlists for `pod_contracts`
and `pod_config`, purity of `pod_geometry`/`pod_guidance`/`pod_state`, and sole
serial-handle ownership by `pod_mavlink`.

**Reasoning.** `[PRD 7.2]` says *"Enforce this in review."* Review is necessary and
not sufficient — the violations that matter arrive as a one-line import in a hurried
patch, which is exactly what a tired reviewer waves through. `[PRD 2.3]` calls the
boundaries *"what makes the system testable and the safety argument auditable"*; an
auditable argument should not rest on recollection. Hard invariant 7 in particular
begins its life as a second `import pymavlink`, and that import can be refused
mechanically.

**Trade-offs accepted.** AST inspection catches **imports**, not intent: a module
could still reach a banned capability through a dynamic import or an injected object.
The test is a floor, not a ceiling, and review still matters. Editing
`rules.py` is editing the architecture, so it needs a decision-log entry — a friction
that is deliberate. Function-level imports count as violations too, since a boundary
crossed lazily is still crossed.

**Alternatives considered.** (a) Review only, as the PRD says — no cost, no floor.
(b) A third-party import-linter (`import-linter`, `grimp`) — more capable, another
dependency, and its contract syntax is one more thing to learn; the AST walk here is
about 120 lines and reads like the PRD table it enforces. (c) Runtime import hooks —
catches dynamic access, at the price of magic in the flight software.

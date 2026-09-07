# Contributing

## Branches

| Kind | Pattern | Example |
|---|---|---|
| Feature | `<initials>/<phase>-<slug>` | `hg/m2-state-machine` |
| Fix | `<initials>/fix-<slug>` | `sg/fix-fisheye-undistort` |
| Decision-only | `<initials>/decision-<nnnn>` | `hg/decision-0019-flight-lens` |

`main` is always green: lint, types and tests pass.

## Before you push

```bash
make check      # ruff + mypy + pytest — the same thing CI runs
```

## Pull requests

Keep them small enough to review properly. Every PR states:

1. **What phase this belongs to** (P0 / M1 / … ). Work that belongs to a later phase
   does not get merged early — `[PRD 7.1]` *"Phases run sequentially. No phase begins
   until the previous phase's exit gate is demonstrated, not merely believed."*
2. **Which decisions it touches**, if any.
3. **Whether it changes a contract** — if so, it needs review from all three module
   owners and a `CONTRACT_VERSION` bump.

### Reviewer checklist

- [ ] No module boundary crossed (the architecture tests cover imports; you cover
      intent)
- [ ] Pure modules stayed pure: no clock, no I/O, no hidden state
- [ ] Every cross-module message still carries capture timestamp **and** frame
      sequence number
- [ ] Nothing else acquired a serial handle — **invariant 7**
- [ ] No number was invented. If a value is not in a project document or a
      measurement, it is `OPEN`
- [ ] Any behaviour touching the seven hard invariants has a test citing its clause

## Decisions

Every hardware or architecture fork gets a decision-log entry: date, decision,
reasoning, **trade-offs accepted**, alternatives considered `[PRD 7.1]`. *"An entry
that records only the outcome is not useful six months later."*

- Weakening a hard invariant needs an entry **and sign-off** `[PRD 1.3]`.
- Editing `tests/architecture/rules.py` is editing the architecture — entry required.
- An open decision closes by a new numbered entry, never by quietly editing
  `open_decisions.md`.

## The house rule about numbers

If a value is not in a project document and has not been measured, it stays `OPEN` in
config and raises at the point of use. Do not substitute something plausible. A
plausible number is indistinguishable from a measured one six months later, and this
project has already paid twice for reversals it could not reconstruct.

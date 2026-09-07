# Decision log

Mandated by [PRD 5.5, 7.1]. It lives in-repo, alongside the code it justifies,
because *"this project has already reversed camera selection three times. Without a
written record of why each choice was made, those reversals cost the same analysis
twice."*

**Steward:** Person A (Hrushikesh) — 🟡 proposed under OD-16, to be confirmed by the
team.

## Format — every entry carries all five fields

[PRD 7.1]: *"Every entry needs a date, the decision, the reasoning, what was given
up, and what else was considered. An entry that records only the outcome is not
useful six months later."*

| Field | Meaning |
|---|---|
| **Date** | When the decision was taken (not when it was written up) |
| **Decision** | What was decided, in one sentence |
| **Reasoning** | Why |
| **Trade-offs accepted** | What was given up |
| **Alternatives considered** | What else was on the table, and why it lost |

Plus, for traceability: **Status**, **Owner**, **Source**, and where relevant
**Expiry** and **Supersedes**.

## Status values

| Status | Meaning |
|---|---|
| `CLOSED` | Decided. Reopening it needs a new entry that supersedes this one. |
| `INTERIM` | Decided **with an expiry**. It stops being valid at the named gate. |
| `DEFERRED` | Deliberately not decided yet, with a named trigger for taking it up. |
| `PROPOSED` | Written down, **not yet agreed**. Needs sign-off before it counts. |

⚠ A `PROPOSED` entry is not a decision. `0007` is `PROPOSED` and weakens a hard
invariant; [PRD 1.3] requires a decision-log entry **and sign-off** for that.

## Rules

1. Every hardware or architecture fork produces an entry [PRD 7.1].
2. Every phase exit gate requires its entries to be written before the gate passes.
3. Weakening any of the seven hard invariants [PRD 1.3] requires an entry **and**
   sign-off.
4. Entries are append-only. A decision is reversed by a **new** entry that says so —
   never by editing history.
5. Open decisions live in [`open_decisions.md`](open_decisions.md), not here. An item
   moves here when it closes.

## Numbering

`NNNN-short-slug.md`, four digits, allocated in order. `0001`–`0018` were imported
from the Implementation 0 planning baseline on 2026-09-07 and record decisions taken
earlier; their **Date** fields are the dates the decisions were actually taken.

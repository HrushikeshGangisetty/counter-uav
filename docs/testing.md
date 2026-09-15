# Testing guide

`python -m pytest`, or `make test`. Everything runs without hardware.

## Layout

| Directory | What it checks | Fails when |
|---|---|---|
| `tests/architecture/` | The `[PRD 2.3, 7.2]` module boundaries, purity, sole serial ownership | Someone crosses a boundary |
| `tests/contracts/` | Every cross-module message carries the stamp; no duplicate definitions; JSON round-trips; schema files match the dataclasses | A contract drifts |
| `tests/unit/` | Per-module behaviour, plus the executable specs below | Behaviour regresses |
| `tests/replay/` | The replay harness over `fixtures/replay/*.jsonl` | Fixtures or the codec break |

## Determinism is the point

`[PRD 2.3]`: *"a logged flight can be replayed offline for bit-identical guidance
output, which turns tuning questions into unit tests instead of flight tests."*

So: no test reads a clock, the network, or hardware. Synthetic sequences are
generated from a `Scenario` with no RNG. `pod_state` and `pod_guidance` take
`now_ns` as an **argument** — that is why `tests/architecture/test_purity.py` fails a
pure module that calls `time.monotonic()`.

## xfail is a ledger, not a fudge

Tests named `test_spec_*.py` are marked `xfail(strict=True)` with a reason naming the
phase and owner. They are the **acceptance criteria for M2, written before the
implementation**. Two properties matter:

- while the behaviour is missing they `xfail`, so CI is green and the suite is honest
  about what does not exist yet;
- `xfail_strict = true`, so the moment the behaviour lands the test **XPASSes and CI
  goes red**, forcing whoever implemented it to delete the marker. The ledger cannot
  rot.

Today's specs: the governor going silent on every documented precondition failure,
the state machine's mode-dependent terminal behaviour, and geometry passing the frame
stamp through.

## Fixtures

`fixtures/replay/*.jsonl` — one `TrackFrame` per line. Regenerate with
`make fixtures` (`scripts/make_fixtures.py`); output is byte-identical everywhere and
CI fails if a regeneration produces a diff.

| Fixture | Shape |
|---|---|
| `closing_target.jsonl` | 120 frames, target growing from ~0.1% to 40% of frame |
| `track_dropout.jsonl` | 60 frames with a 15-frame dropout — drives LOCKED → LOST |
| `empty_sky.jsonl` | 30 frames, no tracks at all |

⚠ These are **synthetic image-space sequences, not measurements.** They deliberately
encode no assumption about lens, range or target size — those are OD-19 and OD-06
questions, and inventing them here would put fabricated numbers into everyone's tests.

See [`docs/synthetic_replay.md`](synthetic_replay.md) for the full synthetic
frame -> detection -> image-coordinates -> camera-ray path, including the
static-position scenarios and what is REAL vs SYNTHETIC vs OPEN in it.

## Adding tests

1. If it needs a clock, hardware, the network or a file, it does not belong in a pure
   module's test — pass the value in.
2. Cite the PRD or ARCH clause in the docstring. A safety test without a citation
   cannot be audited.
3. New cross-module message → add it to `pod_contracts.CROSS_MODULE_MESSAGES`, or
   `tests/contracts/` will not know to check it.

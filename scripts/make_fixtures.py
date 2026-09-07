#!/usr/bin/env python3
"""Regenerate the deterministic replay fixtures under fixtures/.

Run from the repo root:  python scripts/make_fixtures.py
Output is byte-identical on every machine; commit the result.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from simulation.replay import write_track_frames  # noqa: E402
from simulation.synthetic import Scenario, closing_target, generate  # noqa: E402

SCENARIOS = (
    ("closing_target", closing_target(frames=120)),
    (
        "track_dropout",
        Scenario(name="track_dropout", frames=60, dropout_frames=tuple(range(20, 35))),
    ),
    ("empty_sky", Scenario(name="empty_sky", frames=30, dropout_frames=tuple(range(30)))),
)


def main() -> int:
    out_dir = ROOT / "fixtures" / "replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, scenario in SCENARIOS:
        path = out_dir / f"{name}.jsonl"
        n = write_track_frames(path, generate(scenario))
        print(f"wrote {n:4d} frames -> {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

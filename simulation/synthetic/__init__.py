"""Synthetic detection input --- lets M2 work start with no camera and no model.

[PRD 4.3] M2 is driven by "hand-fed synthetic detection sequences"; [DAY1 1] calls
for "a synthetic-detection replayer (a fake moving bbox/track) to drive the whole
thing end-to-end in SITL".

Deterministic by construction: no clocks, no RNG without an explicit seed. The same
scenario yields byte-identical frames on every run, which is what makes the pure
modules replay-testable [PRD 2.3].
"""

from __future__ import annotations

from .generator import Scenario, closing_target, generate

__all__ = ["Scenario", "closing_target", "generate"]

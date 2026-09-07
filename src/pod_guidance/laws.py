"""Guidance laws behind one interface. PURE --- no I/O, no threads, no globals."""

from __future__ import annotations

from collections.abc import Callable

from pod_contracts import GuidanceInput, VelocityCommand

#: The one signature every guidance law has. Adding a law means adding an entry to
#: LAWS --- never a new call site, never an if/else in the control loop [PRD 6.1].
GuidanceLaw = Callable[[GuidanceInput], VelocityCommand]


def pursuit(gi: GuidanceInput) -> VelocityCommand:
    """Proportional pursuit --- centres the target in frame.

    ⚠ NOT IMPLEMENTED --- M2, Person A. The law used M1-M5 [PRD 6.1].
    Gains are per-airframe configuration; none are invented here.
    """
    raise NotImplementedError("pod_guidance.pursuit: M2 / Person A")


def proportional_navigation(gi: GuidanceInput) -> VelocityCommand:
    """Proportional navigation --- commands lateral acceleration proportional to the
    line-of-sight rotation rate, driving toward collision rather than toward the
    target's current position.

    ⚠ NOT IMPLEMENTED --- M6, Person A, and BLOCKED on OD-06: PN needs closing
    velocity, which needs range rate, which monocular vision cannot observe
    [PRD 6.1]. Registered now solely so the switch is a configuration change.
    """
    raise NotImplementedError("pod_guidance.proportional_navigation: M6 / Person A (OD-06)")


LAWS: dict[str, GuidanceLaw] = {
    "pursuit": pursuit,
    "proportional_navigation": proportional_navigation,
}


def get_law(name: str) -> GuidanceLaw:
    """Select a law by configured name. Pure lookup."""
    try:
        return LAWS[name]
    except KeyError as exc:
        raise KeyError(f"unknown guidance law {name!r}; known: {sorted(LAWS)}") from exc

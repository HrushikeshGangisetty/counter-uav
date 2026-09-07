"""pod_guidance --- pursuit and proportional-navigation laws.

Owner: Person A (Hrushikesh).
[PRD 2.3] Must never import: GStreamer, pymavlink.
[PRD 2.3, 7.2] PURE: no I/O, no threads, no globals.

[PRD 6.1] is a design requirement from day one: proportional navigation must sit
BEHIND THE SAME INTERFACE as the pursuit law, so switching is a configuration change
rather than a rewrite --- even though PN is not needed until M6. That is what the
LAWS registry in laws.py exists for. Pure pursuit is a tail chase and is adequate for
surveillance (M1-M5); it is not adequate for intercept, and PN needs closing
velocity, which needs range rate, which is OD-06.
"""

from __future__ import annotations

from .laws import LAWS, GuidanceLaw, get_law, proportional_navigation, pursuit

__all__ = ["LAWS", "GuidanceLaw", "get_law", "proportional_navigation", "pursuit"]

"""pod_guidance: PN sits behind the same interface as pursuit [PRD 6.1].

"Implement proportional navigation behind the same interface as the pursuit law so
that switching is a configuration change rather than a rewrite. This is a design
requirement on pod_guidance from the start, even though the law itself is not needed
until M6."
"""

from __future__ import annotations

import inspect

import pytest

from pod_guidance import LAWS, get_law, proportional_navigation, pursuit


def test_both_laws_are_registered() -> None:
    assert set(LAWS) == {"pursuit", "proportional_navigation"}


def test_laws_share_one_signature() -> None:
    assert inspect.signature(pursuit) == inspect.signature(proportional_navigation)


def test_law_is_selected_by_name_not_by_branching() -> None:
    assert get_law("pursuit") is pursuit
    assert get_law("proportional_navigation") is proportional_navigation


def test_unknown_law_is_refused() -> None:
    with pytest.raises(KeyError):
        get_law("dead_reckoning")

"""[PRD 2.3, 7.2] every cross-module message carries the capture timestamp and the
frame sequence number.

This is the rule the [DAY1 0] draft schema broke (CF-10 / OD-17): it carried
frame_ts but no sequence number. The rule is now a test, so it cannot be broken
again by accident.
"""

from __future__ import annotations

import dataclasses

import pytest

from pod_contracts import CROSS_MODULE_MESSAGES, STAMP_EXEMPT_MESSAGES, FrameMeta


def _field_types(cls) -> dict[str, object]:
    return {f.name: f.type for f in dataclasses.fields(cls)}


@pytest.mark.parametrize("cls", CROSS_MODULE_MESSAGES, ids=lambda c: c.__name__)
def test_carries_capture_timestamp_and_sequence(cls) -> None:
    names = set(_field_types(cls))
    carries_frame = "frame" in names
    carries_flat = {"capture_ts_ns", "frame_seq"} <= names
    assert carries_frame or carries_flat, (
        f"{cls.__name__} carries neither a FrameMeta nor a flat "
        "(capture_ts_ns, frame_seq) pair [PRD 7.2]"
    )


def test_frame_meta_defines_both_fields() -> None:
    names = set(_field_types(FrameMeta))
    assert {"capture_ts_ns", "frame_seq"} <= names


@pytest.mark.parametrize("cls", CROSS_MODULE_MESSAGES, ids=lambda c: c.__name__)
def test_messages_are_frozen(cls) -> None:
    """Messages are values, not shared mutable state [PRD 7.2 single-writer]."""
    assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"


def test_exemptions_are_declared_not_implicit() -> None:
    assert STAMP_EXEMPT_MESSAGES, "exemptions must be listed explicitly, with a reason"
    overlap = set(STAMP_EXEMPT_MESSAGES) & set(CROSS_MODULE_MESSAGES)
    assert not overlap, f"a message cannot be both stamped and exempt: {overlap}"

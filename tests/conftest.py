"""Shared pytest fixtures. Deterministic: no clocks, no network, no hardware."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation import mocks

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def configs_dir() -> Path:
    return REPO_ROOT / "configs"


@pytest.fixture
def fixtures_dir() -> Path:
    return REPO_ROOT / "fixtures"


@pytest.fixture
def track_frame():
    return mocks.make_track_frame()


@pytest.fixture
def vehicle_state():
    return mocks.make_vehicle_state()


@pytest.fixture
def rc_state():
    return mocks.make_rc_state()


@pytest.fixture
def state_input():
    return mocks.make_state_input()


@pytest.fixture(autouse=True)
def _reset_config_latch():
    """pod_config is boot-time immutable; clear the latch between tests."""
    from pod_config import reset_for_tests

    reset_for_tests()
    yield
    reset_for_tests()

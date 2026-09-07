"""pod_mavlink.scheduler.FixedRateScheduler: the 20 Hz driver.

[PRD 1.1], [ARCH Control] the pod offers a setpoint at 20 Hz. Timing is tested with
an injected fake clock so no real time passes and the behaviour is deterministic:
drift-free deadlines, exactly one tick per period, no busy-spin when a tick runs
long, clean stop.
"""

from __future__ import annotations

import pytest

from pod_mavlink import COMMAND_RATE_HZ
from pod_mavlink.scheduler import FixedRateScheduler


class _FakeClock:
    """now_ns advances only when sleep() is called (or a tick advances it)."""

    def __init__(self) -> None:
        self.ns = 0
        self.sleeps: list[float] = []

    def now(self) -> int:
        return self.ns

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.ns += int(seconds * 1_000_000_000)


def test_nominal_rate_is_20hz() -> None:
    sched = FixedRateScheduler(COMMAND_RATE_HZ, lambda _now: None)
    assert sched.rate_hz == 20
    assert sched.period_ns == 50_000_000
    assert sched.period_s == pytest.approx(0.05)


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError, match="positive"):
        FixedRateScheduler(0, lambda _now: None)


def test_runs_exactly_max_ticks_one_call_per_tick() -> None:
    clock = _FakeClock()
    seen: list[int] = []
    sched = FixedRateScheduler(
        20, lambda now: seen.append(now), now_ns=clock.now, sleep=clock.sleep
    )
    sched.run(max_ticks=5)
    assert sched.tick_count == 5
    assert len(seen) == 5
    assert sched.missed_deadlines == 0


def test_ticks_are_spaced_one_period_apart() -> None:
    clock = _FakeClock()
    seen: list[int] = []
    sched = FixedRateScheduler(
        20, lambda now: seen.append(now), now_ns=clock.now, sleep=clock.sleep
    )
    sched.run(max_ticks=4)
    deltas = [b - a for a, b in zip(seen, seen[1:], strict=False)]
    assert deltas == [50_000_000, 50_000_000, 50_000_000]
    assert clock.sleeps == [pytest.approx(0.05)] * 4


def test_long_tick_counts_a_missed_deadline_and_does_not_busy_spin() -> None:
    clock = _FakeClock()

    def slow_tick(_now: int) -> None:
        clock.ns += 80_000_000  # 80 ms > 50 ms period

    sched = FixedRateScheduler(20, slow_tick, now_ns=clock.now, sleep=clock.sleep)
    sched.run(max_ticks=3)
    assert sched.tick_count == 3
    assert sched.missed_deadlines == 3
    # never slept a negative amount, never slept at all while behind
    assert clock.sleeps == []
    assert sched.max_tick_duration_ns >= 80_000_000


def test_stop_from_inside_a_tick_returns_promptly() -> None:
    clock = _FakeClock()
    sched = FixedRateScheduler(20, lambda _now: None, now_ns=clock.now, sleep=clock.sleep)

    calls = {"n": 0}

    def tick(_now: int) -> None:
        calls["n"] += 1
        if calls["n"] == 3:
            sched.stop()

    sched._tick = tick  # type: ignore[assignment]
    sched.run()  # no max_ticks --- must still terminate
    assert calls["n"] == 3
    assert sched.tick_count == 3


def test_external_stop_event_ends_the_run() -> None:
    import threading

    clock = _FakeClock()
    ev = threading.Event()
    n = {"count": 0}

    def tick(_now: int) -> None:
        n["count"] += 1
        if n["count"] == 2:
            ev.set()

    sched = FixedRateScheduler(20, tick, now_ns=clock.now, sleep=clock.sleep)
    sched.run(stop_event=ev)
    assert n["count"] == 2


def test_a_raising_tick_stops_the_scheduler_and_propagates() -> None:
    clock = _FakeClock()

    def boom(_now: int) -> None:
        raise RuntimeError("control tick failed")

    sched = FixedRateScheduler(20, boom, now_ns=clock.now, sleep=clock.sleep)
    with pytest.raises(RuntimeError, match="control tick failed"):
        sched.run(max_ticks=10)
    # the failing tick did not complete, so no successful tick was counted
    assert sched.tick_count == 0

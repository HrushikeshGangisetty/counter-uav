"""pod_mavlink.supervisor.ControlSupervisor --- the [PRD 5.5] control-thread watchdog.

Determinism strategy:

* the failure/health *logic* is tested with ``run_monitor=False`` + a fake clock +
  explicit ``poll_once()`` calls --- no dependence on wall-clock timing;
* the thread-level behaviour (clean shutdown, concurrent stop, exit detection while
  blocking in ``run()``) is tested with real threads but a fast scheduler / small
  poll interval, and only ever asserts on the *outcome*, which is deterministic.

The supervisor must never transmit, never build a command, never substitute zero
velocity. On failure it stops the scheduler and reports; FC-side failsafe does the
rest.
"""

from __future__ import annotations

import threading
import time

import pytest

from pod_config import ConfigOpenError
from pod_contracts import FlightMode, MissionMode, PodState
from pod_mavlink import (
    ControlHealth,
    ControlLoop,
    ControlSupervisor,
    FixedRateScheduler,
    MavlinkLink,
    PerceptionInputs,
    require_watchdog_timeout_ns,
    watchdog_timeout_ns_from_envelope,
)
from simulation.mocks import (
    make_rc_state,
    make_safety_envelope,
    make_vehicle_state,
    make_velocity_command,
)


class _FakeClock:
    def __init__(self) -> None:
        self.ns = 0

    def now(self) -> int:
        return self.ns

    def sleep(self, seconds: float) -> None:
        self.ns += int(seconds * 1_000_000_000)


class _FakeScheduler:
    """Stands in for FixedRateScheduler: a blocking run(), a stop(), a tick_count."""

    def __init__(self) -> None:
        self.tick_count = 0
        self.stopped = False
        self._stop = threading.Event()
        self._raise: BaseException | None = None
        self._exit_early = threading.Event()

    def run(self, *, max_ticks: int | None = None, stop_event: object = None) -> None:
        while not self._stop.is_set():
            if self._raise is not None:
                raise self._raise
            if self._exit_early.is_set():
                return
            time.sleep(0.002)

    def stop(self) -> None:
        self._stop.set()
        self.stopped = True

    def advance(self, n: int = 1) -> None:
        self.tick_count += n


def _wait(predicate, timeout_s: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return False


# --------------------------------------------------------------------------------
# envelope helpers
# --------------------------------------------------------------------------------


def test_watchdog_timeout_from_envelope_is_none_when_open() -> None:
    assert watchdog_timeout_ns_from_envelope(make_safety_envelope()) is None


def test_watchdog_timeout_from_envelope_resolves_when_set() -> None:
    env = make_safety_envelope(control_watchdog_timeout_ms=250.0)
    assert watchdog_timeout_ns_from_envelope(env) == 250_000_000


def test_require_watchdog_timeout_raises_on_open() -> None:
    with pytest.raises(ConfigOpenError, match="OD-A2"):
        require_watchdog_timeout_ns(make_safety_envelope())


# --------------------------------------------------------------------------------
# deterministic health logic (no monitor thread)
# --------------------------------------------------------------------------------


def test_healthy_while_ticks_advance() -> None:
    clock = _FakeClock()
    sched = _FakeScheduler()
    sup = ControlSupervisor(sched, watchdog_timeout_ns=1_000_000, now_ns=clock.now)
    sup.start(run_monitor=False)
    try:
        for _ in range(10):
            sched.advance()
            clock.ns += 400_000  # < timeout, and progress resets the window
            assert sup.poll_once() is ControlHealth.HEALTHY
        assert sup.failure_reason is None
        assert sched.stopped is False
    finally:
        sup.stop()


def test_watchdog_triggers_on_no_progress() -> None:
    clock = _FakeClock()
    sched = _FakeScheduler()
    seen: list = []
    sup = ControlSupervisor(
        sched, watchdog_timeout_ns=1_000_000, now_ns=clock.now, on_failure=seen.append
    )
    sup.start(run_monitor=False)
    try:
        assert sup.poll_once() is ControlHealth.RUNNING
        clock.ns += 2_000_000  # past the timeout, no advance()
        assert sup.poll_once() is ControlHealth.WATCHDOG_TRIGGERED
        assert sched.stopped is True
        assert sup.failure_reason is not None and "no tick progress" in sup.failure_reason
        assert len(seen) == 1 and seen[0].health is ControlHealth.WATCHDOG_TRIGGERED
        assert sup.wait(timeout=1.0) is ControlHealth.WATCHDOG_TRIGGERED
        # a second poll does not re-fire the callback
        sup.poll_once()
        assert len(seen) == 1
    finally:
        sup.stop()


def test_watchdog_does_not_falsely_trigger_during_healthy_operation() -> None:
    clock = _FakeClock()
    sched = _FakeScheduler()
    sup = ControlSupervisor(sched, watchdog_timeout_ns=1_000_000, now_ns=clock.now)
    sup.start(run_monitor=False)
    try:
        for _ in range(50):
            sched.advance()
            clock.ns += 900_000  # 0.9 ms < 1.0 ms timeout, every cycle
            health = sup.poll_once()
            assert health in (ControlHealth.RUNNING, ControlHealth.HEALTHY)
        assert sup.health is ControlHealth.HEALTHY
    finally:
        sup.stop()


def test_progress_watchdog_disabled_when_timeout_is_none() -> None:
    clock = _FakeClock()
    sched = _FakeScheduler()
    sup = ControlSupervisor(sched, watchdog_timeout_ns=None, now_ns=clock.now)
    assert sup.watchdog_enabled is False
    sup.start(run_monitor=False)
    try:
        clock.ns += 10_000_000_000  # 10 s of "no progress"
        for _ in range(5):
            assert sup.poll_once() is ControlHealth.RUNNING
    finally:
        sup.stop()


def test_unexpected_scheduler_exit_is_failure() -> None:
    clock = _FakeClock()
    sched = _FakeScheduler()
    seen: list = []
    sup = ControlSupervisor(
        sched, watchdog_timeout_ns=None, now_ns=clock.now, on_failure=seen.append
    )
    sched._exit_early.set()
    sup.start(run_monitor=False)
    try:
        assert _wait(lambda: sup._control_done.is_set())
        assert sup.poll_once() is ControlHealth.FAILED
        assert sup.failure_reason is not None and "unexpectedly" in sup.failure_reason
        assert sched.stopped is True
        assert len(seen) == 1
    finally:
        sup.stop()


def test_tick_exception_is_failure_with_reason() -> None:
    clock = _FakeClock()
    sched = _FakeScheduler()
    sched._raise = RuntimeError("wedged tick")
    sup = ControlSupervisor(sched, watchdog_timeout_ns=None, now_ns=clock.now)
    sup.start(run_monitor=False)
    try:
        assert _wait(lambda: sup._control_done.is_set())
        assert sup.poll_once() is ControlHealth.FAILED
        assert sup.failure_reason is not None and "wedged tick" in sup.failure_reason
    finally:
        sup.stop()


def test_terminal_state_is_not_downgraded_by_stop() -> None:
    clock = _FakeClock()
    sched = _FakeScheduler()
    sup = ControlSupervisor(sched, watchdog_timeout_ns=1_000_000, now_ns=clock.now)
    sup.start(run_monitor=False)
    clock.ns += 5_000_000
    assert sup.poll_once() is ControlHealth.WATCHDOG_TRIGGERED
    sup.stop()  # must NOT become STOPPED
    assert sup.health is ControlHealth.WATCHDOG_TRIGGERED


def test_start_twice_raises() -> None:
    sup = ControlSupervisor(_FakeScheduler(), watchdog_timeout_ns=None)
    sup.start(run_monitor=False)
    try:
        with pytest.raises(RuntimeError, match="already started"):
            sup.start(run_monitor=False)
    finally:
        sup.stop()


# --------------------------------------------------------------------------------
# thread-level behaviour (monitor on) --- deterministic outcomes only
# --------------------------------------------------------------------------------


def test_clean_shutdown_via_stop() -> None:
    clock = _FakeClock()
    sched = FixedRateScheduler(2000, lambda _n: None, now_ns=clock.now, sleep=clock.sleep)
    sup = ControlSupervisor(
        sched, watchdog_timeout_ns=None, now_ns=clock.now, poll_interval_s=0.005
    )
    sup.start()
    assert _wait(lambda: sup.health in (ControlHealth.RUNNING, ControlHealth.HEALTHY))
    sup.stop()
    assert sup.health is ControlHealth.STOPPED
    assert sup.running is False
    sup.stop()  # idempotent
    assert sup.health is ControlHealth.STOPPED


def test_bounded_run_finishes_as_stopped() -> None:
    clock = _FakeClock()
    sched = FixedRateScheduler(2000, lambda _n: None, now_ns=clock.now, sleep=clock.sleep)
    sup = ControlSupervisor(
        sched, watchdog_timeout_ns=None, now_ns=clock.now, poll_interval_s=0.005
    )
    health = sup.run(max_ticks=5)
    assert health is ControlHealth.STOPPED
    assert sched.tick_count == 5
    assert sup.running is False


def test_race_safe_concurrent_stop() -> None:
    clock = _FakeClock()
    sched = FixedRateScheduler(5000, lambda _n: None, now_ns=clock.now, sleep=clock.sleep)
    sup = ControlSupervisor(
        sched, watchdog_timeout_ns=None, now_ns=clock.now, poll_interval_s=0.005
    )
    sup.start()
    assert _wait(lambda: sup.health in (ControlHealth.RUNNING, ControlHealth.HEALTHY))

    errors: list[BaseException] = []

    def _stop() -> None:
        try:
            sup.stop()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_stop) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)

    assert not errors
    assert all(not t.is_alive() for t in threads)
    assert sup.health is ControlHealth.STOPPED
    assert sup.running is False


def test_exit_detection_works_even_with_watchdog_disabled() -> None:
    clock = _FakeClock()

    def boom(_now_ns: int) -> None:
        raise RuntimeError("control tick failed")

    sched = FixedRateScheduler(2000, boom, now_ns=clock.now, sleep=clock.sleep)
    sup = ControlSupervisor(
        sched, watchdog_timeout_ns=None, now_ns=clock.now, poll_interval_s=0.005
    )
    health = sup.run()
    assert health is ControlHealth.FAILED
    assert sup.failure_reason is not None and "control tick failed" in sup.failure_reason


# --------------------------------------------------------------------------------
# the safety property: no transmission / no stale resend after failure
# --------------------------------------------------------------------------------


class _FakeMav:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    def set_position_target_local_ned_send(self, **fields: object) -> None:
        self.sent.append(fields)


class _FakeConn:
    def __init__(self) -> None:
        self.mav = _FakeMav()

    def close(self) -> None:
        pass


class _FakeRx:
    def __init__(self, vehicle, rc) -> None:
        self._v = vehicle
        self._r = rc

    def snapshot(self):
        return self._v, self._r


def _visible_target(_now_ns: int) -> PerceptionInputs:
    return PerceptionInputs(
        frame=None,
        proposed_command=make_velocity_command(),
        target_visible=True,
        bbox_area_fraction=0.01,
        locked_track_id=1,
    )


def test_no_mavlink_transmission_and_no_stale_resend_after_failure() -> None:
    clock = _FakeClock()
    link = MavlinkLink(device="udp:127.0.0.1:14550")
    conn = _FakeConn()
    link._conn = conn
    rx = _FakeRx(
        make_vehicle_state(mode=FlightMode.GUIDED),
        make_rc_state(ai_enable=True, lock_trigger=True, kill_switch=False),
    )
    loop = ControlLoop(
        link=link,
        rx=rx,
        envelope=make_safety_envelope(
            bbox_area_terminal=0.30, bbox_area_breakoff=0.45, max_frame_age_ms=250.0
        ),
        mission_mode=MissionMode.SURVEILLANCE,
        target_system=1,
        target_component=1,
        command_source=_visible_target,
        state=PodState.LOCKED,
        now_ns=clock.now,
    )

    calls = {"n": 0}
    real_tick = loop.tick

    def tick(now_ns: int):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("control thread wedged")
        return real_tick(now_ns)

    sched = FixedRateScheduler(2000, tick, now_ns=clock.now, sleep=clock.sleep)
    sup = ControlSupervisor(
        sched, watchdog_timeout_ns=None, now_ns=clock.now, poll_interval_s=0.005
    )
    health = sup.run()

    assert health is ControlHealth.FAILED
    # ticks 1 and 2 transmitted a fresh SEND each; tick 3 raised before its send
    assert len(conn.mav.sent) == 2
    assert conn.mav.sent[0] is not conn.mav.sent[1]  # distinct messages, not a resend
    frozen = list(conn.mav.sent)
    time.sleep(0.05)
    assert conn.mav.sent == frozen  # nothing sent after the failure, nothing resent

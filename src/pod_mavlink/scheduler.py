"""A fixed-rate driver for the control cycle. Knows nothing about the pod.

`[PRD 1.1]`, `[ARCH Control]` the pod offers a setpoint at **20 Hz**. This class is
the loop that calls *something* on that cadence; what it calls (the ``ControlLoop``
tick) is passed in. Keeping the two apart means the timing behaviour --- drift-free
deadlines, no busy-spin, bounded catch-up --- is unit-testable with an injected fake
clock, and the control cycle is testable without any real time passing.

Timing model: deadline ``n`` is ``start + n * period``. After each tick the loop
sleeps until the next deadline. If a tick runs long the missed deadline is counted
and the loop moves straight to the next tick --- it never sleeps a negative amount
and never tries to "make up" the lost ticks in a burst.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

_log = logging.getLogger("pod_mavlink.scheduler")

#: A tick callback: given the loop's current ``now_ns`` reading, run one cycle.
Tick = Callable[[int], object]


class FixedRateScheduler:
    """Call ``tick(now_ns)`` at ``rate_hz`` until stopped or ``max_ticks`` reached."""

    def __init__(
        self,
        rate_hz: float,
        tick: Tick,
        *,
        now_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_hz <= 0:
            raise ValueError("FixedRateScheduler: rate_hz must be positive")
        self.rate_hz = rate_hz
        self.period_ns = round(1_000_000_000 / rate_hz)
        self._tick = tick
        self._now_ns = now_ns
        self._sleep = sleep
        self._stop = threading.Event()
        #: Observability --- read by tests and by the SITL harness after ``run()``.
        self.tick_count = 0
        self.missed_deadlines = 0
        self.last_tick_duration_ns = 0
        self.max_tick_duration_ns = 0

    @property
    def period_s(self) -> float:
        return self.period_ns / 1_000_000_000

    def stop(self) -> None:
        """Ask ``run()`` to return after the current tick. Safe from any thread."""
        self._stop.set()

    def run(
        self,
        *,
        max_ticks: int | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        """Block, ticking at the target rate, until:

        * ``stop()`` is called (or ``self._stop`` / the passed ``stop_event`` is set),
        * ``max_ticks`` ticks have run, whichever comes first.
        """
        self._stop.clear()
        start_ns = self._now_ns()
        n = 0
        while not self._stop.is_set() and not (stop_event is not None and stop_event.is_set()):
            if max_ticks is not None and n >= max_ticks:
                break

            t0 = self._now_ns()
            try:
                self._tick(t0)
            except Exception:
                # The tick raising is the pod going silent [PRD 4.3]: stop ticking and
                # let the FC's own GUIDED setpoint timeout take over. Re-raise so the
                # caller (supervisor.ControlSupervisor) sees it and reports FAILED.
                self._stop.set()
                _log.exception("control tick raised; scheduler stopping")
                raise
            duration = self._now_ns() - t0
            self.last_tick_duration_ns = duration
            self.max_tick_duration_ns = max(self.max_tick_duration_ns, duration)
            self.tick_count += 1
            n += 1

            deadline_ns = start_ns + n * self.period_ns
            slack_ns = deadline_ns - self._now_ns()
            if slack_ns > 0:
                self._sleep(slack_ns / 1_000_000_000)
            else:
                self.missed_deadlines += 1
                # No sleep, no burst catch-up: the next tick's own deadline is still
                # start_ns + (n+1) * period, so the loop self-corrects once ticks fit
                # in the period again.

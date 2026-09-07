"""Control-thread supervisor. `[PRD 5.5]`

    "A live process with a dead control thread is the dangerous case."

`FixedRateScheduler.run()` already stops (and re-raises) when a tick raises --- that
produces pod silence. What it does not do is *notice* the silence: a caller that ran
the scheduler on a thread and walked away would never learn the control loop had
died, and nothing would confirm the pod had actually gone quiet.

`ControlSupervisor` is that confirmation. It owns the control thread, watches two
independent failure signals, and on either one it **stops the scheduler and reports**
--- nothing else. It never touches the MAVLink link, never builds a command, never
substitutes zero velocity. Stopping the scheduler stops the ticks, which stops the
`MavlinkLink.send()` calls; there is no retransmit buffer anywhere, so "no stale
command is resent" is a property of *not ticking*, not of anything the supervisor
clears. The FC's own ~3 s GUIDED setpoint timeout `[PRD 4.3, 5.4]` then takes over,
exactly as it does for every other precondition failure.

The two signals:

* **Unexpected exit** --- the control thread finished when the supervisor did not ask
  it to and no ``max_ticks`` bound was reached (a raising tick, or ``run()``
  returning early for any reason). Always active.
* **No progress** --- ``FixedRateScheduler.tick_count`` has not advanced for longer
  than the watchdog timeout. Active **only when a timeout is configured**; the
  production value is OPEN (OD-A2, ``SafetyEnvelope.control_watchdog_timeout_ms``),
  so on a real pod today only unexpected-exit detection runs, and that gap is logged
  loudly at start.

This module adds no safety *policy*: it does not re-decide anything
``pod_state.govern()`` decides, and a governed SILENT tick is perfectly healthy
progress as far as the supervisor is concerned. It only answers "is the loop that
runs the governor still alive and moving".
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from pod_config import ConfigOpenError, SafetyEnvelope

from .scheduler import FixedRateScheduler

_log = logging.getLogger("pod_mavlink.supervisor")


class ControlHealth(str, Enum):
    """Observable control-loop health. String-valued for clean logging."""

    STARTING = "starting"  #: start() called, control thread not yet confirmed running
    RUNNING = "running"  #: control thread alive, no completed cycle observed yet
    HEALTHY = "healthy"  #: control thread alive and tick_count advancing
    STOPPED = "stopped"  #: clean shutdown --- stop() requested, or a bounded run finished
    FAILED = "failed"  #: control thread exited when it should not have
    WATCHDOG_TRIGGERED = "watchdog_triggered"  #: no tick progress within the timeout


_TERMINAL = (ControlHealth.STOPPED, ControlHealth.FAILED, ControlHealth.WATCHDOG_TRIGGERED)


@dataclass(frozen=True, slots=True)
class SupervisorReport:
    """A snapshot of supervisor state. Internal observability, not a contract."""

    health: ControlHealth
    reason: str | None
    tick_count: int
    observed_ns: int
    watchdog_enabled: bool

    def as_log_fields(self) -> dict[str, object]:
        return {
            "health": self.health.value,
            "reason": self.reason,
            "ticks": self.tick_count,
            "watchdog": "on" if self.watchdog_enabled else "off(OPEN)",
        }


def watchdog_timeout_ns_from_envelope(envelope: SafetyEnvelope) -> int | None:
    """Resolve the no-progress timeout from boot config, or ``None`` if it is OPEN.

    ``None`` is a valid, documented state (OD-A2): the supervisor then runs
    unexpected-exit detection only. Callers that would rather refuse to start without
    a real value can use :func:`require_watchdog_timeout_ns` instead.
    """
    value = envelope.control_watchdog_timeout_ms
    if not isinstance(value, (int, float)):  # OPEN sentinel
        return None
    return int(float(value) * 1_000_000)


def require_watchdog_timeout_ns(envelope: SafetyEnvelope) -> int:
    """Like :func:`watchdog_timeout_ns_from_envelope`, but raise ``ConfigOpenError``
    if the value is still OPEN rather than degrading to exit-only detection."""
    resolved = watchdog_timeout_ns_from_envelope(envelope)
    if resolved is None:
        raise ConfigOpenError(
            "SafetyEnvelope.control_watchdog_timeout_ms is OPEN (OD-A2); the "
            "control-thread progress watchdog has no timeout to run against"
        )
    return resolved


class ControlSupervisor:
    """Owns and watches the control thread that runs a ``FixedRateScheduler``.

    Lifecycle: ``start()`` / ``stop()``, or ``run()`` for a blocking convenience, or
    as a context manager. ``poll_once()`` runs exactly one health evaluation and is
    what the monitor thread calls on a timer --- tests drive it directly with
    ``run_monitor=False`` for fully deterministic assertions.
    """

    def __init__(
        self,
        scheduler: FixedRateScheduler,
        *,
        watchdog_timeout_ns: int | None,
        now_ns: Callable[[], int] = time.monotonic_ns,
        poll_interval_s: float = 0.05,
        on_failure: Callable[[SupervisorReport], None] | None = None,
        join_timeout_s: float = 2.0,
    ) -> None:
        self._scheduler = scheduler
        self._watchdog_timeout_ns = watchdog_timeout_ns
        self._now_ns = now_ns
        self._poll_interval_s = poll_interval_s
        self._on_failure = on_failure
        self._join_timeout_s = join_timeout_s

        self._lock = threading.Lock()
        self._health = ControlHealth.STARTING
        self._reason: str | None = None
        self._finished = threading.Event()

        self._control_thread: threading.Thread | None = None
        self._monitor_thread: threading.Thread | None = None
        self._control_done = threading.Event()
        self._control_exc: BaseException | None = None
        self._monitor_stop = threading.Event()
        self._stop_requested = False
        self._max_ticks: int | None = None

        #: progress tracking, guarded by ``_lock``
        self._last_count = 0
        self._last_progress_ns = 0

    # -- observability ---------------------------------------------------------

    @property
    def watchdog_enabled(self) -> bool:
        return self._watchdog_timeout_ns is not None

    @property
    def health(self) -> ControlHealth:
        with self._lock:
            return self._health

    @property
    def failure_reason(self) -> str | None:
        with self._lock:
            return self._reason

    @property
    def running(self) -> bool:
        t = self._control_thread
        return t is not None and t.is_alive()

    def report(self) -> SupervisorReport:
        with self._lock:
            return SupervisorReport(
                health=self._health,
                reason=self._reason,
                tick_count=self._scheduler.tick_count,
                observed_ns=self._now_ns(),
                watchdog_enabled=self._watchdog_timeout_ns is not None,
            )

    # -- lifecycle ----------------------------------------------------------------

    def start(self, *, max_ticks: int | None = None, run_monitor: bool = True) -> None:
        if self._control_thread is not None:
            raise RuntimeError("pod_mavlink.ControlSupervisor.start: already started")
        self._max_ticks = max_ticks
        with self._lock:
            self._last_count = self._scheduler.tick_count
            self._last_progress_ns = self._now_ns()
            self._health = ControlHealth.RUNNING
        self._control_thread = threading.Thread(
            target=self._control_main, name="pod-control", daemon=True
        )
        self._control_thread.start()
        if self._watchdog_timeout_ns is None:
            _log.warning(
                "control supervisor started: progress watchdog DISABLED "
                "(SafetyEnvelope.control_watchdog_timeout_ms is OPEN, OD-A2); "
                "unexpected-exit detection is active"
            )
        else:
            _log.info(
                "control supervisor started: watchdog_timeout_ns=%d",
                self._watchdog_timeout_ns,
            )
        if run_monitor:
            self._monitor_thread = threading.Thread(
                target=self._monitor_main, name="pod-control-watchdog", daemon=True
            )
            self._monitor_thread.start()

    def run(self, *, max_ticks: int | None = None) -> ControlHealth:
        """Blocking: start, wait for the control loop to end (cleanly or not), return
        the final health. The monitor thread runs so a stall is still detected."""
        self.start(max_ticks=max_ticks, run_monitor=True)
        self.wait()
        return self.health

    def wait(self, timeout: float | None = None) -> ControlHealth:
        """Block until health is terminal (or ``timeout`` elapses)."""
        self._finished.wait(timeout)
        return self.health

    def stop(self, *, reason: str = "requested") -> None:
        """Idempotent, race-safe. Signals the scheduler and monitor, joins both.

        A failure the monitor already latched (FAILED / WATCHDOG_TRIGGERED) is **not**
        downgraded to STOPPED --- the first terminal state wins. A control-thread
        exception observed during shutdown still resolves to FAILED.
        """
        with self._lock:
            first_call = not self._stop_requested
            self._stop_requested = True
        self._scheduler.stop()
        self._monitor_stop.set()
        self._join(self._monitor_thread)
        self._join(self._control_thread)
        with self._lock:
            if self._health not in _TERMINAL:
                if self._control_exc is not None:
                    self._health = ControlHealth.FAILED
                    self._reason = f"control thread raised: {self._control_exc!r}"
                else:
                    self._health = ControlHealth.STOPPED
                    self._reason = reason
            final_health, final_reason = self._health, self._reason
        self._finished.set()
        if first_call:
            _log.info(
                "control supervisor stopped: health=%s reason=%s", final_health.value, final_reason
            )

    def __enter__(self) -> ControlSupervisor:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    # -- control thread --------------------------------------------------------

    def _control_main(self) -> None:
        try:
            self._scheduler.run(max_ticks=self._max_ticks)
        except BaseException as exc:  # noqa: BLE001 --- captured, classified, re-surfaced as health
            self._control_exc = exc
            _log.exception("control thread raised")
        finally:
            self._control_done.set()

    # -- monitor thread --------------------------------------------------------

    def _monitor_main(self) -> None:
        while not self._monitor_stop.is_set() and not self._finished.is_set():
            self.poll_once()
            self._monitor_stop.wait(self._poll_interval_s)

    def poll_once(self) -> ControlHealth:
        """One health evaluation. Latches a terminal state (and stops the scheduler +
        fires ``on_failure``) on the first failure it sees; a no-op afterwards."""
        failure_report: SupervisorReport | None = None
        with self._lock:
            if self._health in _TERMINAL:
                return self._health

            if self._control_done.is_set():
                if self._control_exc is not None:
                    failure_report = self._latch(
                        ControlHealth.FAILED,
                        f"control thread raised: {self._control_exc!r}",
                    )
                elif self._stop_requested:
                    self._health = ControlHealth.STOPPED
                    self._reason = "requested"
                elif self._max_ticks is not None and self._scheduler.tick_count >= self._max_ticks:
                    self._health = ControlHealth.STOPPED
                    self._reason = f"completed {self._max_ticks} ticks"
                else:
                    failure_report = self._latch(
                        ControlHealth.FAILED, "control thread exited unexpectedly"
                    )
                if self._health in _TERMINAL and failure_report is None:
                    self._finished.set()
                    return self._health

            if failure_report is None:
                count = self._scheduler.tick_count
                now = self._now_ns()
                if count != self._last_count:
                    self._last_count = count
                    self._last_progress_ns = now
                    if self._health is ControlHealth.RUNNING:
                        self._health = ControlHealth.HEALTHY
                        _log.debug("control loop healthy: ticks=%d", count)
                elif self._watchdog_timeout_ns is not None:
                    stalled_ns = now - self._last_progress_ns
                    if stalled_ns > self._watchdog_timeout_ns:
                        failure_report = self._latch(
                            ControlHealth.WATCHDOG_TRIGGERED,
                            f"no tick progress for {stalled_ns} ns "
                            f"(> {self._watchdog_timeout_ns} ns), ticks={count}",
                        )

        if failure_report is not None:
            self._scheduler.stop()
            self._monitor_stop.set()
            self._finished.set()
            _log.error("control loop %s", failure_report.as_log_fields())
            if self._on_failure is not None:
                try:
                    self._on_failure(failure_report)
                except Exception:  # noqa: BLE001 --- a broken callback must not mask the failure
                    _log.exception("on_failure callback raised")
        with self._lock:
            return self._health

    def _latch(self, health: ControlHealth, reason: str) -> SupervisorReport:
        """Set a terminal health + reason under ``_lock`` and build its report."""
        self._health = health
        self._reason = reason
        return SupervisorReport(
            health=health,
            reason=reason,
            tick_count=self._scheduler.tick_count,
            observed_ns=self._now_ns(),
            watchdog_enabled=self._watchdog_timeout_ns is not None,
        )

    def _join(self, thread: threading.Thread | None) -> None:
        if thread is not None and thread.is_alive():
            thread.join(timeout=self._join_timeout_s)
            if thread.is_alive():
                _log.warning(
                    "%s did not exit within %.1fs; pod is silent, FC failsafe in effect",
                    thread.name,
                    self._join_timeout_s,
                )

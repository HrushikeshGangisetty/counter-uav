"""Wire the pod runtime to an ArduPilot SITL (or any MAVLink endpoint) and run it.

This is **dev scaffolding**, not flight software --- ``src/pod_*`` may not import it
(``tests/architecture/test_import_boundaries.py``). It exists so the exact
``pod_mavlink`` + ``pod_state`` path that will later face a real FC can be exercised
against a simulator today.

What is SITL-specific and lives only here:

* the connection string (from ``sitl.yaml``; a localhost UDP placeholder, not a
  project decision);
* obviously-synthetic ``SafetyEnvelope`` / ``MissionMode`` / RC-channel numbers ---
  the shipped config leaves these OPEN (OD-12, mission latch, RC map), and the house
  rule forbids guessing them in ``src``. A simulator harness supplying clearly-fake
  values to make the path runnable is the same pattern the unit tests use.

What is **not** re-implemented here: the RX decode, the scheduler, the control cycle
and the governor all come straight from ``pod_mavlink`` / ``pod_state``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pod_config import RCChannelMap, SafetyEnvelope
from pod_contracts import MissionMode, VelocityCommand
from pod_mavlink import (
    COMMAND_RATE_HZ,
    ControlHealth,
    ControlLoop,
    ControlSupervisor,
    FixedRateScheduler,
    MavlinkLink,
    MavlinkRxRuntime,
    PerceptionInputs,
    SupervisorReport,
    null_command_source,
)
from simulation.mocks import make_frame, make_safety_envelope

_log = logging.getLogger("simulation.sitl.harness")

_SITL_YAML = Path(__file__).with_name("sitl.yaml")

#: SITL/MAVLink convention for a single autopilot. Not a project decision --- the
#: harness talks to one simulated vehicle. ``MavlinkLink.send()`` itself has no
#: default here (decision 0021); the harness is the caller that supplies it.
_SITL_TARGET_SYSTEM = 1
_SITL_TARGET_COMPONENT = 1

#: Obviously-synthetic RC channel numbers, used ONLY so the harness can decode SITL's
#: RC_CHANNELS. The real map is OPEN (no document assigns channels).
_SITL_RC_CHANNELS = RCChannelMap(
    ai_enable_channel=6,
    lock_trigger_channel=7,
    kill_switch_channel=8,
    mission_mode_channel=9,
    high_threshold_us=1800,
)


def load_sitl_config(path: Path = _SITL_YAML) -> dict[str, Any]:
    """Parse ``sitl.yaml``. ``OPEN`` fields (home, ardupilot_root) come back as-is and
    are not used by this harness --- it only needs ``connection``."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def synthetic_envelope() -> SafetyEnvelope:
    """A fully-populated envelope with clearly-not-measured values, for SITL only."""
    return make_safety_envelope(
        bbox_area_terminal=0.30,
        bbox_area_breakoff=0.45,
        max_frame_age_ms=250.0,
    )


#: ⚠ NOT the production value. OD-A2 (SafetyEnvelope.control_watchdog_timeout_ms) is
#: OPEN and needs the M3 measured control-cycle distribution behind it. This 1 s
#: figure exists ONLY so a SITL run can exercise the progress-watchdog path; it is
#: deliberately far larger than a 20 Hz (50 ms) cycle so it never trips on jitter.
#: Never copy it into configs/ or treat it as measured.
_SIM_WATCHDOG_TIMEOUT_NS = 1_000_000_000


def synthetic_watchdog_timeout_ns() -> int:
    """The SITL-only no-progress timeout. See ``_SIM_WATCHDOG_TIMEOUT_NS`` --- this is
    scaffolding, not the OD-A2 decision."""
    return _SIM_WATCHDOG_TIMEOUT_NS


def constant_pursuit_source(
    *, vx_ms: float = 3.0, bbox_area_fraction: float = 0.05
) -> Callable[[int], PerceptionInputs]:
    """A stand-in for the perception/geometry/guidance chain: always "target visible,
    here is a small fixed forward velocity". Lets the SEND path run in SITL when RC +
    mode permit it. Not guidance --- a constant vector, nothing closed-loop."""
    command = VelocityCommand(
        frame=make_frame(seq=0), vx_ms=vx_ms, vy_ms=0.0, vz_ms=0.0, yaw_rate_rads=0.0
    )

    def _source(_now_ns: int) -> PerceptionInputs:
        return PerceptionInputs(
            frame=make_frame(seq=0),
            proposed_command=command,
            target_visible=True,
            bbox_area_fraction=bbox_area_fraction,
            locked_track_id=1,
        )

    return _source


@dataclass
class SitlHarness:
    """Open a link, start the RX thread, drive the control loop at ``rate_hz``.

    Use as a context manager, or ``start()`` / ``run()`` / ``stop()`` by hand.
    """

    connection: str | None = None
    rate_hz: float = COMMAND_RATE_HZ
    mission_mode: MissionMode = MissionMode.SURVEILLANCE
    envelope: SafetyEnvelope | None = None
    command_source: Callable[[int], PerceptionInputs] = null_command_source
    decode_rc: bool = True
    now_ns: Callable[[], int] = time.monotonic_ns
    #: None -> progress watchdog disabled (OD-A2 OPEN), unexpected-exit detection
    #: only. Pass ``synthetic_watchdog_timeout_ns()`` to exercise the stall path.
    watchdog_timeout_ns: int | None = None

    def __post_init__(self) -> None:
        cfg = load_sitl_config()
        self.connection = self.connection or str(cfg.get("connection", "udp:127.0.0.1:14550"))
        self.envelope = self.envelope or synthetic_envelope()
        self.link = MavlinkLink(self.connection)
        self.rx: MavlinkRxRuntime | None = None
        self.loop: ControlLoop | None = None
        self.scheduler: FixedRateScheduler | None = None
        self.supervisor: ControlSupervisor | None = None
        self.last_failure: SupervisorReport | None = None

    # -- lifecycle ----------------------------------------------------------------

    def start(self) -> None:
        self.link.open()
        _log.info("sitl link open: %s", self.connection)
        assert self.envelope is not None
        self.rx = MavlinkRxRuntime(
            self.link,
            boot_ts_ns=self.now_ns(),
            rc_channels=_SITL_RC_CHANNELS if self.decode_rc else None,
            now_ns=self.now_ns,
        )
        self.rx.start()
        self.loop = ControlLoop(
            link=self.link,
            rx=self.rx,
            envelope=self.envelope,
            mission_mode=self.mission_mode,
            target_system=_SITL_TARGET_SYSTEM,
            target_component=_SITL_TARGET_COMPONENT,
            command_source=self.command_source,
            now_ns=self.now_ns,
        )
        self.scheduler = FixedRateScheduler(self.rate_hz, self.loop.tick, now_ns=self.now_ns)
        self.supervisor = ControlSupervisor(
            self.scheduler,
            watchdog_timeout_ns=self.watchdog_timeout_ns,
            now_ns=self.now_ns,
            on_failure=self._on_control_failure,
        )

    def _on_control_failure(self, report: SupervisorReport) -> None:
        self.last_failure = report
        _log.error("sitl control-loop failure: %s", report.as_log_fields())

    def run(
        self, *, duration_s: float | None = None, max_ticks: int | None = None
    ) -> ControlHealth:
        if self.supervisor is None:
            raise RuntimeError("SitlHarness.run: call start() first")
        if max_ticks is None and duration_s is not None:
            max_ticks = int(duration_s * self.rate_hz)
        health = self.supervisor.run(max_ticks=max_ticks)
        scheduler = self.scheduler
        assert scheduler is not None
        _log.info(
            "sitl run done: health=%s ticks=%d missed_deadlines=%d rx_seen=%d",
            health.value,
            scheduler.tick_count,
            scheduler.missed_deadlines,
            self.rx.messages_seen if self.rx else -1,
        )
        return health

    def stop(self) -> None:
        if self.supervisor is not None:
            self.supervisor.stop()
        elif self.scheduler is not None:
            self.scheduler.stop()
        if self.rx is not None:
            self.rx.stop()
        self.link.close()
        _log.info("sitl harness stopped")

    def __enter__(self) -> SitlHarness:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

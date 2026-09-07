"""The MAVLink RX runtime: the thread and read loop around the pure ``rx`` builders.

`[PRD 7.2]` the RX thread is the **single writer** of ``VehicleState`` and
``RCState``. ``rx.py`` is the whole of "what happens to the value" for each message
type, decoupled from any socket; this module is the socket read loop that calls it,
plus the thread that owns the loop and the lock that makes ``snapshot()`` safe for
other threads to read.

Split, deliberately:

* **decode stays in ``rx.py``** --- pure, synthetic-testable, no pymavlink;
* **I/O and threading live here** --- ``MavlinkLink.recv()`` for the read, one
  ``threading.Thread`` for the loop, one ``threading.Lock`` for the hand-off.

This module holds **no safety policy**. It never decides whether a command may be
sent; it only turns received messages into the two state dataclasses the governor
later reads. Missing or malformed messages leave the last good value in place (or the
fail-safe initial value if nothing has arrived yet) --- they never fabricate a
"healthy" state.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from pod_config import ConfigOpenError, RCChannelMap, is_open
from pod_contracts import FlightMode, RCState, VehicleState

from .link import MavlinkLink
from .rx import (
    apply_attitude,
    apply_heartbeat,
    apply_local_position_ned,
    initial_rc_state,
    initial_vehicle_state,
    rc_state_from_channels,
)

_log = logging.getLogger("pod_mavlink.rx_runtime")

#: The message types the RX loop asks ``MavlinkLink.recv()`` for. VFR_HUD is in
#: [PRD 5.4]'s SRx trim list but has no ``rx`` builder (airspeed/throttle are not in
#: ``VehicleState``), so it is not requested here.
RX_MESSAGE_TYPES: tuple[str, ...] = (
    "HEARTBEAT",
    "ATTITUDE",
    "LOCAL_POSITION_NED",
    "RC_CHANNELS",
)

#: [MAVLink common.xml, MAV_MODE_FLAG enum] the "armed" bit of HEARTBEAT.base_mode.
#: A wire-format constant, fixed by the protocol --- hard-coding it is implementing a
#: spec, not inventing a number (same basis as ``MAV_FRAME_BODY_NED = 8`` in
#: setpoint.py, per decision 0021).
_MAV_MODE_FLAG_SAFETY_ARMED = 0x80

#: How long a single blocking ``recv()`` waits before the loop re-checks its stop
#: flag. Not a project decision: purely how responsive ``stop()`` is, bounded well
#: under the [PRD 1.3 invariant 3] 500 ms heartbeat window so a stuck link is noticed
#: by the governor (via staleness), not hidden by a long blocking read here.
_RECV_TIMEOUT_S = 0.1

#: How long ``stop()`` waits for the loop thread to exit before it logs and returns.
_JOIN_TIMEOUT_S = 2.0

ModeDecoder = Callable[[MavlinkLink, Any], FlightMode]


def default_mode_decoder(link: MavlinkLink, _heartbeat_msg: Any) -> FlightMode:
    """Map the FC's mode to ``FlightMode``: GUIDED, or OTHER for everything else.

    Reads pymavlink's own resolved ``link.flightmode`` string rather than decoding
    ``custom_mode`` here --- see ``MavlinkLink.flightmode``. Anything that is not
    exactly ``"GUIDED"`` is OTHER, which fails safe: the governor honours pod
    setpoints only in GUIDED [PRD 1.3 invariant 2].
    """
    try:
        return FlightMode.GUIDED if link.flightmode == "GUIDED" else FlightMode.OTHER
    except Exception:  # noqa: BLE001 --- a mode we cannot read is, safely, "not GUIDED"
        return FlightMode.OTHER


def _resolve_rc_channels(rc: RCChannelMap) -> dict[str, int]:
    """Turn an ``RCChannelMap`` into the plain ints ``rc_state_from_channels`` needs,
    raising ``ConfigOpenError`` if any is still OPEN.

    [house rule] channel numbers are OPEN in the shipped config (no document assigns
    them). The RX runtime refuses to guess: a caller that wants real RC decoding must
    supply a fully-resolved map, or pass ``rc_channels=None`` and accept that RCState
    stays at its fail-safe initial value (kill_switch=True) forever.
    """
    fields = (
        "ai_enable_channel",
        "lock_trigger_channel",
        "kill_switch_channel",
        "high_threshold_us",
    )
    resolved: dict[str, int] = {}
    for name in fields:
        value = getattr(rc, name)
        if is_open(value):
            raise ConfigOpenError(
                f"pod_mavlink.rx_runtime: RCChannelMap.{name} is OPEN; the RX runtime "
                "refuses to decode RC_CHANNELS against a guessed channel number. "
                "Resolve it, or construct the runtime with rc_channels=None."
            )
        resolved[name] = int(value)
    return resolved


class MavlinkRxRuntime:
    """Owns the RX loop thread and the current ``VehicleState`` / ``RCState``.

    Construct with an **open** ``MavlinkLink``. ``start()`` spawns one daemon thread;
    ``stop()`` joins it. ``snapshot()`` returns the current pair, safe to call from
    any thread. The two dataclasses are frozen, so a reader always sees a consistent
    value; the lock only guards the writer's reassignment against a torn read on
    interpreters without the GIL.
    """

    def __init__(
        self,
        link: MavlinkLink,
        *,
        boot_ts_ns: int,
        rc_channels: RCChannelMap | None = None,
        now_ns: Callable[[], int] = time.monotonic_ns,
        mode_decoder: ModeDecoder = default_mode_decoder,
        recv_timeout_s: float = _RECV_TIMEOUT_S,
        join_timeout_s: float = _JOIN_TIMEOUT_S,
    ) -> None:
        self._link = link
        self._now_ns = now_ns
        self._mode_decoder = mode_decoder
        self._recv_timeout_s = recv_timeout_s
        self._join_timeout_s = join_timeout_s
        self._rc_fields: dict[str, int] | None = (
            _resolve_rc_channels(rc_channels) if rc_channels is not None else None
        )

        self._lock = threading.Lock()
        self._vehicle = initial_vehicle_state(boot_ts_ns)
        self._rc = initial_rc_state(boot_ts_ns)

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        #: Cheap observability counters --- read by tests and by the SITL harness.
        self.messages_seen = 0
        self.messages_ignored = 0
        self.last_heartbeat_recv_ts_ns: int | None = None

    # -- lifecycle -------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("pod_mavlink.MavlinkRxRuntime.start: already started")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pod-mavlink-rx", daemon=True)
        self._thread.start()
        _log.info("rx runtime started (recv_timeout_s=%s)", self._recv_timeout_s)

    def stop(self) -> None:
        """Idempotent. Signals the loop, joins the thread, logs if it will not exit."""
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=self._join_timeout_s)
            if thread.is_alive():
                _log.warning(
                    "rx runtime thread did not exit within %.1fs of stop()",
                    self._join_timeout_s,
                )
            self._thread = None
        _log.info(
            "rx runtime stopped (seen=%d ignored=%d)",
            self.messages_seen,
            self.messages_ignored,
        )

    def __enter__(self) -> MavlinkRxRuntime:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- reader side --------------------------------------------------------------

    def snapshot(self) -> tuple[VehicleState, RCState]:
        """The current ``(VehicleState, RCState)``. Safe from any thread."""
        with self._lock:
            return self._vehicle, self._rc

    # -- writer side (loop thread only) ----------------------------------------

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self._link.recv(timeout_s=self._recv_timeout_s)
            except Exception:  # noqa: BLE001
                # A read error is loss of the link, not loss of the vehicle
                # [PRD 1.3 invariant 3]. Log, keep the last good state, and let the
                # governor reject it on staleness. Do not tear the thread down on a
                # transient.
                _log.exception("rx recv failed; keeping last good state")
                self._stop.wait(self._recv_timeout_s)
                continue
            if msg is None:
                continue
            self._dispatch(msg)

    def _dispatch(self, msg: Any) -> None:
        try:
            msg_type = msg.get_type()
        except Exception:  # noqa: BLE001
            self.messages_ignored += 1
            return
        self.messages_seen += 1
        recv_ts_ns = self._now_ns()
        try:
            if msg_type == "HEARTBEAT":
                self._on_heartbeat(msg, recv_ts_ns)
            elif msg_type == "ATTITUDE":
                self._on_attitude(msg, recv_ts_ns)
            elif msg_type == "LOCAL_POSITION_NED":
                self._on_local_position_ned(msg, recv_ts_ns)
            elif msg_type == "RC_CHANNELS":
                self._on_rc_channels(msg, recv_ts_ns)
            else:
                self.messages_ignored += 1
        except (AttributeError, TypeError, ValueError):
            # A message that is missing a field, or carries a wrong type, is dropped.
            # The previous good state stands --- never a fabricated substitute.
            _log.warning("dropping malformed %s message", msg_type)
            self.messages_ignored += 1

    def _on_heartbeat(self, msg: Any, recv_ts_ns: int) -> None:
        mode = self._mode_decoder(self._link, msg)
        armed = bool(int(msg.base_mode) & _MAV_MODE_FLAG_SAFETY_ARMED)
        with self._lock:
            self._vehicle = apply_heartbeat(
                self._vehicle, recv_ts_ns=recv_ts_ns, mode=mode, armed=armed
            )
        self.last_heartbeat_recv_ts_ns = recv_ts_ns
        _log.debug("heartbeat mode=%s armed=%s ts=%d", mode.value, armed, recv_ts_ns)

    def _on_attitude(self, msg: Any, recv_ts_ns: int) -> None:
        with self._lock:
            self._vehicle = apply_attitude(
                self._vehicle,
                recv_ts_ns=recv_ts_ns,
                roll_rad=float(msg.roll),
                pitch_rad=float(msg.pitch),
                yaw_rad=float(msg.yaw),
                roll_rate_rads=float(msg.rollspeed),
                pitch_rate_rads=float(msg.pitchspeed),
                yaw_rate_rads=float(msg.yawspeed),
            )

    def _on_local_position_ned(self, msg: Any, recv_ts_ns: int) -> None:
        with self._lock:
            self._vehicle = apply_local_position_ned(
                self._vehicle,
                recv_ts_ns=recv_ts_ns,
                pos_north_m=float(msg.x),
                pos_east_m=float(msg.y),
                pos_down_m=float(msg.z),
                vel_north_ms=float(msg.vx),
                vel_east_ms=float(msg.vy),
                vel_down_ms=float(msg.vz),
            )

    def _on_rc_channels(self, msg: Any, recv_ts_ns: int) -> None:
        if self._rc_fields is None:
            # No resolved channel map: RC stays at its fail-safe initial value.
            self.messages_ignored += 1
            return
        count = int(msg.chancount)
        raw = tuple(int(getattr(msg, f"chan{i}_raw")) for i in range(1, count + 1))
        with self._lock:
            self._rc = rc_state_from_channels(
                recv_ts_ns=recv_ts_ns,
                raw_channels=raw,
                ai_enable_channel=self._rc_fields["ai_enable_channel"],
                lock_trigger_channel=self._rc_fields["lock_trigger_channel"],
                kill_switch_channel=self._rc_fields["kill_switch_channel"],
                high_threshold_us=self._rc_fields["high_threshold_us"],
            )

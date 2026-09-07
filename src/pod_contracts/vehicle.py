"""Vehicle and RC state, as received from the flight controller.

Owner: Person A. Producer: the pod_mavlink RX thread, which is the SINGLE WRITER of
both structures [PRD 7.2]. Consumers: pod_geometry (attitude for body-frame
transforms), pod_state, pod_guidance, pod_gcs.

Units: SI. Angles in radians. Velocities in m/s. NED frame (north, east, down).
Timestamps: CLOCK_MONOTONIC nanoseconds at MAVLink message receipt, so staleness is
measurable against the same clock as FrameMeta.capture_ts_ns.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import FlightMode

#: [PRD 1.3 invariant 3] a heartbeat gap beyond this constitutes loss of the pod's
#: view of the vehicle. 500 ms, expressed in nanoseconds.
HEARTBEAT_GAP_LIMIT_NS = 500_000_000


@dataclass(frozen=True, slots=True)
class VehicleState:
    """Vehicle attitude/position/mode snapshot. Written only by the MAVLink RX thread."""

    recv_ts_ns: int
    last_heartbeat_ts_ns: int
    mode: FlightMode
    armed: bool
    roll_rad: float
    pitch_rad: float
    yaw_rad: float
    roll_rate_rads: float
    pitch_rate_rads: float
    yaw_rate_rads: float
    pos_north_m: float
    pos_east_m: float
    pos_down_m: float
    vel_north_ms: float
    vel_east_ms: float
    vel_down_ms: float

    def heartbeat_ok(self, now_ns: int) -> bool:
        return (now_ns - self.last_heartbeat_ts_ns) <= HEARTBEAT_GAP_LIMIT_NS


@dataclass(frozen=True, slots=True)
class RCState:
    """Pilot RC switch state, decoded from RC_CHANNELS by pod_mavlink.

    [PRD 1.3 invariant 4] engagement requires ai_enable AND lock_trigger; neither
    alone is sufficient. mission_mode is latched at takeoff and is carried here only
    so the state machine can assert it has not changed [invariant 5]; it is not a
    runtime control.
    """

    recv_ts_ns: int
    ai_enable: bool
    lock_trigger: bool
    kill_switch: bool
    raw_channels: tuple[int, ...] = ()

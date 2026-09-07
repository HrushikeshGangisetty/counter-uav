"""Pure builders for VehicleState / RCState from already-decoded MAVLink fields.

No pymavlink here: these take the plain numeric fields a decoded HEARTBEAT/ATTITUDE/
LOCAL_POSITION_NED/RC_CHANNELS message already carries, not a pymavlink message
object, so they are testable with synthetic values on any machine --- no hardware, no
pymavlink installed.

[PRD 7.2] the RX thread is the SINGLE WRITER of VehicleState and RCState. The RX
thread itself (M3, not built in this slice --- it needs a live serial port to read)
is expected to hold one VehicleState and one RCState variable and reassign it with
the return value of these functions as each relevant message arrives; the functions
here are the whole of "what happens to the value", decoupled from the socket read
loop that will eventually call them.
"""

from __future__ import annotations

import dataclasses

from pod_contracts import HEARTBEAT_GAP_LIMIT_NS, FlightMode, RCState, VehicleState


def initial_vehicle_state(boot_ts_ns: int) -> VehicleState:
    """The RX thread's starting value, before any MAVLink message has arrived.

    Deliberately already stale [PRD 1.3 invariant 3]: last_heartbeat_ts_ns is set
    HEARTBEAT_GAP_LIMIT_NS + 1 before boot_ts_ns, so heartbeat_ok(boot_ts_ns) is
    False immediately. "Go silent" [PRD 4.3] applies just as much to the moment
    before the pod has ever heard from the FC as to a loss after it has --- there is
    no reason the governor should trust an unread VehicleState any more than a stale
    one.
    """
    return VehicleState(
        recv_ts_ns=boot_ts_ns,
        last_heartbeat_ts_ns=boot_ts_ns - HEARTBEAT_GAP_LIMIT_NS - 1,
        mode=FlightMode.UNKNOWN,
        armed=False,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
        roll_rate_rads=0.0,
        pitch_rate_rads=0.0,
        yaw_rate_rads=0.0,
        pos_north_m=0.0,
        pos_east_m=0.0,
        pos_down_m=0.0,
        vel_north_ms=0.0,
        vel_east_ms=0.0,
        vel_down_ms=0.0,
    )


def apply_heartbeat(
    vehicle: VehicleState, *, recv_ts_ns: int, mode: FlightMode, armed: bool
) -> VehicleState:
    """HEARTBEAT updates mode, armed state and the heartbeat staleness clock together
    [PRD 1.3 invariants 2, 3]. ``mode`` arrives already resolved to FlightMode ---
    turning MAVLink's raw custom_mode/autopilot fields into GUIDED-vs-OTHER is
    autopilot-specific message decoding, not this pure builder's job."""
    return dataclasses.replace(
        vehicle,
        recv_ts_ns=recv_ts_ns,
        last_heartbeat_ts_ns=recv_ts_ns,
        mode=mode,
        armed=armed,
    )


def apply_attitude(
    vehicle: VehicleState,
    *,
    recv_ts_ns: int,
    roll_rad: float,
    pitch_rad: float,
    yaw_rad: float,
    roll_rate_rads: float,
    pitch_rate_rads: float,
    yaw_rate_rads: float,
) -> VehicleState:
    """ATTITUDE updates orientation and body rates. Does not touch
    last_heartbeat_ts_ns --- only HEARTBEAT does [PRD 1.3 invariant 3]."""
    return dataclasses.replace(
        vehicle,
        recv_ts_ns=recv_ts_ns,
        roll_rad=roll_rad,
        pitch_rad=pitch_rad,
        yaw_rad=yaw_rad,
        roll_rate_rads=roll_rate_rads,
        pitch_rate_rads=pitch_rate_rads,
        yaw_rate_rads=yaw_rate_rads,
    )


def apply_local_position_ned(
    vehicle: VehicleState,
    *,
    recv_ts_ns: int,
    pos_north_m: float,
    pos_east_m: float,
    pos_down_m: float,
    vel_north_ms: float,
    vel_east_ms: float,
    vel_down_ms: float,
) -> VehicleState:
    """LOCAL_POSITION_NED updates NED position and velocity."""
    return dataclasses.replace(
        vehicle,
        recv_ts_ns=recv_ts_ns,
        pos_north_m=pos_north_m,
        pos_east_m=pos_east_m,
        pos_down_m=pos_down_m,
        vel_north_ms=vel_north_ms,
        vel_east_ms=vel_east_ms,
        vel_down_ms=vel_down_ms,
    )


def initial_rc_state(boot_ts_ns: int) -> RCState:
    """The RX thread's starting RCState, before any RC_CHANNELS message has arrived.

    Fails safe by construction: kill_switch=True and ai_enable/lock_trigger=False, so
    the governor's kill_switch_low/ai_enable_high/lock_trigger_asserted preconditions
    [PRD 1.3 invariant 4] all refuse by default. An RC state nobody has read yet must
    never be treated as "safe to fly".
    """
    return RCState(
        recv_ts_ns=boot_ts_ns,
        ai_enable=False,
        lock_trigger=False,
        kill_switch=True,
        raw_channels=(),
    )


def rc_state_from_channels(
    *,
    recv_ts_ns: int,
    raw_channels: tuple[int, ...],
    ai_enable_channel: int,
    lock_trigger_channel: int,
    kill_switch_channel: int,
    high_threshold_us: int,
) -> RCState:
    """Decode RC_CHANNELS into RCState [PRD 1.3 invariant 4], [ARCH State Machine].

    Channel numbers are 1-based, matching MAVLink RC_CHANNELS (chan1_raw..): channel
    N is ``raw_channels[N - 1]``.

    The three channel numbers and the high threshold are boot-time configuration
    (pod_config.RCChannelMap) --- OPEN in the shipped config today, since no document
    assigns channel numbers (OD, see docs/decisions/open_decisions.md). This function
    therefore takes them already resolved to plain ints; resolving OPEN is the
    caller's job (pod_config.ConfigOpenError already exists for exactly that), not
    something to duplicate here.
    """

    def _high(channel: int) -> bool:
        return raw_channels[channel - 1] >= high_threshold_us

    return RCState(
        recv_ts_ns=recv_ts_ns,
        ai_enable=_high(ai_enable_channel),
        lock_trigger=_high(lock_trigger_channel),
        kill_switch=_high(kill_switch_channel),
        raw_channels=raw_channels,
    )

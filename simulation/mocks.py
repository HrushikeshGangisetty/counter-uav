"""Mock inputs and outputs, so A, B and C can each work without the others.

Every builder returns a fully-formed contract object with deterministic values and no
hardware, no clock and no file access. Import these in tests:

    from simulation.mocks import make_track_frame, make_vehicle_state, make_rc_state

Nothing here is a measurement. The numbers are shaped to be obviously synthetic so
they can never be mistaken for calibration output or flight data.
"""

from __future__ import annotations

from pod_contracts import (
    BBox,
    Detection,
    FlightMode,
    FrameMeta,
    GuidanceInput,
    LineOfSight,
    MissionMode,
    RangeMethod,
    RCState,
    StateInput,
    TrackedObject,
    TrackFrame,
    VehicleState,
    VelocityCommand,
)

NS_PER_FRAME_60HZ = 16_666_667


def make_frame(seq: int = 0, camera_id: int = 0, capture_ts_ns: int | None = None) -> FrameMeta:
    return FrameMeta(
        camera_id=camera_id,
        frame_seq=seq,
        capture_ts_ns=seq * NS_PER_FRAME_60HZ if capture_ts_ns is None else capture_ts_ns,
        width_px=1456,
        height_px=1088,
    )


def make_track_frame(
    seq: int = 0,
    *,
    track_id: int = 1,
    area_fraction: float = 0.01,
    class_name: str = "uav",
    confidence: float = 0.8,
    empty: bool = False,
) -> TrackFrame:
    frame = make_frame(seq)
    if empty:
        return TrackFrame(frame=frame, tracks=())
    side = (area_fraction * frame.width_px * frame.height_px) ** 0.5
    bbox = BBox(
        x_px=(frame.width_px - side) / 2,
        y_px=(frame.height_px - side) / 2,
        w_px=side,
        h_px=side,
    )
    return TrackFrame(
        frame=frame,
        tracks=(
            TrackedObject(
                track_id=track_id,
                detection=Detection(
                    class_id=0, class_name=class_name, confidence=confidence, bbox=bbox
                ),
            ),
        ),
    )


def make_vehicle_state(
    now_ns: int = 0,
    *,
    mode: FlightMode = FlightMode.GUIDED,
    armed: bool = True,
    heartbeat_age_ns: int = 0,
) -> VehicleState:
    return VehicleState(
        recv_ts_ns=now_ns,
        last_heartbeat_ts_ns=now_ns - heartbeat_age_ns,
        mode=mode,
        armed=armed,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
        roll_rate_rads=0.0,
        pitch_rate_rads=0.0,
        yaw_rate_rads=0.0,
        pos_north_m=0.0,
        pos_east_m=0.0,
        pos_down_m=-20.0,
        vel_north_ms=0.0,
        vel_east_ms=0.0,
        vel_down_ms=0.0,
    )


def make_rc_state(
    now_ns: int = 0,
    *,
    ai_enable: bool = True,
    lock_trigger: bool = True,
    kill_switch: bool = False,
) -> RCState:
    return RCState(
        recv_ts_ns=now_ns,
        ai_enable=ai_enable,
        lock_trigger=lock_trigger,
        kill_switch=kill_switch,
        raw_channels=(),
    )


def make_line_of_sight(seq: int = 0, track_id: int = 1) -> LineOfSight:
    return LineOfSight(
        frame=make_frame(seq),
        track_id=track_id,
        los_body_x=1.0,
        los_body_y=0.0,
        los_body_z=0.0,
        bbox_area_fraction=0.01,
        range_method=RangeMethod.NONE,
        range_m=None,
        range_rate_ms=None,
    )


def make_guidance_input(seq: int = 0, law: str = "pursuit") -> GuidanceInput:
    return GuidanceInput(
        frame=make_frame(seq),
        los=make_line_of_sight(seq),
        vehicle=make_vehicle_state(seq * NS_PER_FRAME_60HZ),
        law=law,
    )


def make_velocity_command(seq: int = 0) -> VelocityCommand:
    return VelocityCommand(
        frame=make_frame(seq), vx_ms=0.0, vy_ms=0.0, vz_ms=0.0, yaw_rate_rads=0.0
    )


def make_state_input(
    seq: int = 0,
    *,
    mission_mode: MissionMode = MissionMode.SURVEILLANCE,
    with_command: bool = True,
    **kwargs,
) -> StateInput:
    now_ns = seq * NS_PER_FRAME_60HZ
    return StateInput(
        now_ns=now_ns,
        frame=make_frame(seq),
        vehicle=kwargs.pop("vehicle", make_vehicle_state(now_ns)),
        rc=kwargs.pop("rc", make_rc_state(now_ns)),
        mission_mode=mission_mode,
        proposed_command=make_velocity_command(seq) if with_command else None,
        locked_track_id=kwargs.pop("locked_track_id", 1),
        target_visible=kwargs.pop("target_visible", True),
        bbox_area_fraction=kwargs.pop("bbox_area_fraction", 0.01),
    )

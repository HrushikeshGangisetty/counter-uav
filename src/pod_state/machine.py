"""The eight-state machine.

The transition table below is transcribed verbatim from [ARCH State Machine], which
PRD v1.1 does NOT supersede. It is data, not prose, so tests can assert the
implementation matches the document rather than someone's memory of it.
"""

from __future__ import annotations

from dataclasses import dataclass

from pod_contracts import PodState, StateInput, StateOutput


@dataclass(frozen=True, slots=True)
class Transition:
    """One documented row of [ARCH State Machine]."""

    state: PodState
    description: str
    entry: str
    exit: str


#: Verbatim from [ARCH State Machine] (not superseded by PRD v1.1).
TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        PodState.IDLE,
        "Pod armed, inference off",
        "Boot, or kill switch from any state",
        "AI-enable RC channel high",
    ),
    Transition(
        PodState.SEARCH,
        "Inference running, no lock",
        "AI-enable high",
        "Lock requested AND target detection exists",
    ),
    Transition(
        PodState.LOCKED,
        "Target acquired, pursuit active",
        "Lock event in SEARCH",
        "Target lost > 1.5 s, or pilot unlock",
    ),
    Transition(
        PodState.TERMINAL,
        "Bbox 30-45% of frame, full-commit pursuit",
        "Bbox crosses BBOX_AREA_TERMINAL while LOCKED",
        "Bbox > breakoff threshold, or target lost",
    ),
    Transition(
        PodState.BREAKOFF,
        "Climb + yaw-away manoeuvre (surveillance only)",
        "Bbox > breakoff AND mission = surveillance",
        "Manoeuvre duration expires",
    ),
    Transition(
        PodState.ENGAGE,
        "Continued forward commit (intercept only)",
        "Bbox > breakoff AND mission = intercept",
        "Kinetic event handled by host drone",
    ),
    Transition(
        PodState.LOST,
        "Target ID gone, hover and re-scan",
        "Tracker dropout in LOCKED",
        "Re-acquire, or 5 s timeout -> SEARCH",
    ),
    Transition(
        PodState.ABORT,
        "Pod stops MAVLink writes",
        "Kill switch RC high",
        "Kill switch low -> IDLE",
    ),
)


def step(current: PodState, si: StateInput) -> StateOutput:
    """Advance the state machine one tick. PURE.

    ⚠ NOT IMPLEMENTED --- M2, Person A.

    Contract when implemented:
      * pure and total: every (state, input) pair yields a StateOutput; no exception
        path may leave the caller without a decision;
      * ``si.now_ns`` is the only clock --- never read a clock inside this module, or
        replay stops being bit-identical [PRD 2.3];
      * mission mode is read from si and never written [PRD 1.3 invariant 5];
      * ENGAGE is reachable only when mission mode is INTERCEPT; BREAKOFF only when
        SURVEILLANCE [ARCH State Machine];
      * every returned command passes through govern() before it can be sent.
    """
    raise NotImplementedError("pod_state.step: M2 / Person A")

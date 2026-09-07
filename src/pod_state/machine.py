"""The eight-state machine.

The transition table below is transcribed verbatim from [ARCH State Machine], which
PRD v1.1 does NOT supersede. It is data, not prose, so tests can assert the
implementation matches the document rather than someone's memory of it.
"""

from __future__ import annotations

from dataclasses import dataclass

from pod_config import SafetyEnvelope
from pod_contracts import CommandDecision, MissionMode, PodState, StateInput, StateOutput

from ._envelope import require as _require


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


#: States in which a proposed command may be sent at all. Every other state is a
#: search/hover/stopped posture with nothing to pursue --- SILENT, never a
#: zero-velocity substitute [PRD 4.3].
_SEND_CAPABLE_STATES = (PodState.LOCKED, PodState.TERMINAL)


def _send_or_silent(
    next_state: PodState, transition_reason: str, si: StateInput, previous_state: PodState
) -> StateOutput:
    """Build the StateOutput for a state that MAY send: SEND if there is a proposed
    command to relay, SILENT (never zero-velocity) if there is not."""
    if next_state in _SEND_CAPABLE_STATES and si.proposed_command is not None:
        return StateOutput(
            state=next_state,
            decision=CommandDecision.SEND,
            command=si.proposed_command,
            reason=transition_reason,
            previous_state=previous_state,
        )
    reason = transition_reason if next_state not in _SEND_CAPABLE_STATES else "no_proposed_command"
    return StateOutput(
        state=next_state,
        decision=CommandDecision.SILENT,
        command=None,
        reason=reason,
        previous_state=previous_state,
    )


def _silent(state: PodState, reason: str, previous_state: PodState) -> StateOutput:
    return StateOutput(
        state=state, decision=CommandDecision.SILENT, command=None, reason=reason,
        previous_state=previous_state,
    )


def _step_idle(current: PodState, si: StateInput) -> StateOutput:
    """[ARCH State Machine] IDLE exit: 'AI-enable RC channel high' -> SEARCH."""
    if si.rc.ai_enable:
        return _silent(PodState.SEARCH, "ai_enable_high", current)
    return _silent(PodState.IDLE, "ai_enable_low", current)


def _step_search(current: PodState, si: StateInput) -> StateOutput:
    """[ARCH State Machine] SEARCH exit: 'Lock requested AND target detection
    exists' -> LOCKED. si.rc.lock_trigger is the lock request; si.target_visible is
    the target detection."""
    if si.rc.lock_trigger and si.target_visible:
        return _silent(PodState.LOCKED, "lock_trigger_and_target_visible", current)
    return _silent(PodState.SEARCH, "no_lock", current)


def _step_locked(current: PodState, si: StateInput, envelope: SafetyEnvelope) -> StateOutput:
    """[ARCH State Machine] LOCKED exit: 'Target lost > 1.5 s, or pilot unlock' ->
    LOST / SEARCH. TERMINAL entry: 'Bbox crosses BBOX_AREA_TERMINAL while LOCKED'.

    The '> 1.5 s' debounce is not re-implemented here: si.target_visible is already
    the debounced signal from whatever assembled StateInput (pod_state is pure and
    reads no clock [PRD 2.3, 7.2], so timing against si.now_ns cannot happen inside
    this module) --- reading si.target_visible as-is is not inventing a condition,
    it is using the one StateInput already carries.
    """
    if not si.target_visible:
        return _silent(PodState.LOST, "target_lost", current)
    if not si.rc.lock_trigger:
        return _silent(PodState.SEARCH, "pilot_unlock", current)

    bbox_area_terminal = _require(envelope.bbox_area_terminal, "bbox_area_terminal")
    if si.bbox_area_fraction >= bbox_area_terminal:
        return _send_or_silent(PodState.TERMINAL, "bbox_area_terminal_crossed", si, current)
    return _send_or_silent(PodState.LOCKED, "pursuing", si, current)


def _step_terminal(current: PodState, si: StateInput, envelope: SafetyEnvelope) -> StateOutput:
    """[ARCH State Machine] TERMINAL exit: 'Bbox > breakoff threshold, or target
    lost' -> BREAKOFF (surveillance) / ENGAGE (intercept) / LOST.

    The bbox > breakoff branch is guarded, not implemented: BREAKOFF's own exit is
    blocked on OD-U9 (manoeuvre duration, not stated in any project document) and
    ENGAGE's is blocked on OD-U5 (the kinetic-event boundary is undefined). Reaching
    either state without being able to leave it again would not be advice the FC can
    safely rely on, so this raises rather than returning a state this module cannot
    also exit.
    """
    if not si.target_visible:
        return _silent(PodState.LOST, "target_lost", current)

    bbox_area_breakoff = _require(envelope.bbox_area_breakoff, "bbox_area_breakoff")
    if si.bbox_area_fraction > bbox_area_breakoff:
        if si.mission_mode is MissionMode.SURVEILLANCE:
            raise NotImplementedError(
                "pod_state.step: TERMINAL -> BREAKOFF is M2 / Person A, blocked on "
                "OD-U9 (BREAKOFF manoeuvre duration is not stated in any project "
                "document)"
            )
        raise NotImplementedError(
            "pod_state.step: TERMINAL -> ENGAGE is M2 / Person A, blocked on OD-U5 "
            "('kinetic event handled by host drone' boundary is undefined)"
        )

    return _send_or_silent(PodState.TERMINAL, "terminal_pursuit", si, current)


def _step_lost(current: PodState, si: StateInput) -> StateOutput:
    """[ARCH State Machine] LOST exit: 'Re-acquire, or 5 s timeout -> SEARCH'.

    Only re-acquisition is implemented. The 5 s timeout needs "how long have we been
    in LOST", a duration StateInput does not carry and this module cannot compute
    itself (pure, no clock read [PRD 2.3, 7.2]) --- see OD-U10. This is not a safety
    gap: LOST always emits SILENT, so staying in LOST indefinitely commands nothing,
    exactly as the 5 s timeout path would once it reached SEARCH (also SILENT).
    """
    if si.target_visible and si.rc.lock_trigger:
        return _send_or_silent(PodState.LOCKED, "reacquired", si, current)
    return _silent(PodState.LOST, "awaiting_reacquisition_or_timeout", current)


def _step_abort(current: PodState) -> StateOutput:
    """[ARCH State Machine] ABORT exit: 'Kill switch low -> IDLE'. Reachable only
    when step() has already confirmed the kill switch is low this tick (the
    kill-switch override in step() runs first and unconditionally)."""
    return _silent(PodState.IDLE, "kill_switch_low", current)


def step(current: PodState, si: StateInput, envelope: SafetyEnvelope) -> StateOutput:
    """Advance the state machine one tick. PURE.

    ``envelope`` is the boot-loaded, per-airframe SafetyEnvelope --- passed the same
    way as pod_state.governor.govern() does [decision 0019], for the same reason:
    StateInput is a cross-module contract and threading config through it is its own
    reviewed change, not something to do inside a transition-logic slice.

    Implemented this slice: IDLE, SEARCH, LOCKED, TERMINAL, LOST, ABORT --- every
    transition among them that [ARCH State Machine] states and StateInput can answer
    without inventing a duration, threshold, gain or condition. BREAKOFF and ENGAGE
    raise NotImplementedError naming the open decision that blocks them (OD-U9,
    OD-U5); TERMINAL's exit toward either does too, for the same reason.

    Contract:
      * pure: ``si.now_ns`` is the only clock reference, never read directly, and
        this module holds no state between calls [PRD 2.3, 7.2];
      * mission mode is read from si and never written [PRD 1.3 invariant 5];
      * kill switch high reaches ABORT unconditionally, from any current state,
        before any per-state logic runs;
      * a returned command is a candidate only --- it still passes through govern()
        before it can be sent [PRD 1.3 invariant 1].
    """
    if si.rc.kill_switch:
        return StateOutput(
            state=PodState.ABORT,
            decision=CommandDecision.SILENT,
            command=None,
            reason="kill_switch_high",
            previous_state=current,
        )

    if current is PodState.IDLE:
        return _step_idle(current, si)
    if current is PodState.SEARCH:
        return _step_search(current, si)
    if current is PodState.LOCKED:
        return _step_locked(current, si, envelope)
    if current is PodState.TERMINAL:
        return _step_terminal(current, si, envelope)
    if current is PodState.LOST:
        return _step_lost(current, si)
    if current is PodState.ABORT:
        return _step_abort(current)
    if current is PodState.BREAKOFF:
        raise NotImplementedError(
            "pod_state.step: BREAKOFF exit is M2 / Person A, blocked on OD-U9 "
            "(manoeuvre duration is not stated in any project document)"
        )
    if current is PodState.ENGAGE:
        raise NotImplementedError(
            "pod_state.step: ENGAGE exit is M2 / Person A, blocked on OD-U5 "
            "('kinetic event handled by host drone' boundary is undefined)"
        )
    raise AssertionError(f"pod_state.step: unhandled PodState {current!r}")

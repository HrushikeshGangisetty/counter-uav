"""Model artifact handoff contract --- Person B (Raghava) -> Person A (Hrushikesh).

Owner: Person A, co-authored with Person B during P0 (Document 2 section 6.2).

Scope discipline: only fields supported by a project document are REQUIRED here.
[Doc 2 section 6.2] "A formal model metadata schema does not exist... Items commonly
expected in such a handoff --- anchor configurations, confidence-threshold
recommendations, per-class performance breakdowns, latency-per-layer profiles --- are
NOT required by any project document." Those are absent by choice, not oversight.

Fields marked PROVISIONAL below are carried because the pipeline cannot integrate an
artifact without them, but no document fixes their form yet; they are OPEN.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import NMSLocation


@dataclass(frozen=True, slots=True)
class QuantisationEvidence:
    """Post-quantisation accuracy evidence [PRD 5.3]: "Verify accuracy after
    quantisation, not before."

    OPEN (OD-B3): no project document names an accuracy metric, a threshold, or a
    held-out test set, so none is hard-coded here. metric_name/value are recorded as
    stated by Person B; acceptance is a human gate until OD-B3 closes.
    """

    metric_name: str
    metric_value_fp32: float | None
    metric_value_int8: float | None
    test_set_id: str
    small_object_regime_covered: bool
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ModelArtifactMetadata:
    """CROSS-MODULE MESSAGE (build-time, not per-frame).

    Accompanies every .hef delivered to pod_perception. Required fields are those
    [Doc 2 section 6.1] lists as document-supported.
    """

    # --- REQUIRED, document-supported -------------------------------------------
    artifact_path: str
    input_width_px: int
    input_height_px: int
    nms_location: NMSLocation
    class_names: tuple[str, ...]
    sustained_fps_aggregate: float | None
    known_limitations: str
    quantisation: QuantisationEvidence | None

    # --- PROVISIONAL / OPEN ------------------------------------------------------
    #: OPEN: no versioning or naming convention is specified in any document
    #: (Document 2, section 5.6). Recorded as free text until one is agreed.
    artifact_version: str = ""
    #: OPEN: source architecture and its licence. [Team 2026-09-07] AGPL-3.0 is
    #: deferred, not eliminated --- Person B keeps a one-line licence note per
    #: architecture trialled so the eventual decision is a lookup.
    architecture: str = ""
    licence: str = ""
    sha256: str = ""
    extra: tuple[tuple[str, str], ...] = field(default_factory=tuple)


#: There is no automated accept/reject gate: [Doc 2 section 6.2] "No acceptance gate
#: is defined for Person A to accept or reject a delivered model." Integration is a
#: reviewed human decision until that is agreed. This constant exists so the gap is
#: visible in code rather than only in a document.
MODEL_ACCEPTANCE_GATE = "OPEN"

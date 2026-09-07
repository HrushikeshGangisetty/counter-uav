# Model artifact handoff contract — Person B → Person A

Owner: Person A (Hrushikesh), co-authored with Person B (Raghava) during P0.
Machine form: `pod_contracts.ModelArtifactMetadata` and
[`model_artifact.schema.json`](model_artifact.schema.json).

## Scope discipline — read this first

[Document 2 §6.2]: *"A formal model metadata schema does not exist. No document
specifies a manifest format, required fields, or a versioning convention… Items
commonly expected in such a handoff — anchor configurations, confidence-threshold
recommendations, per-class performance breakdowns, latency-per-layer profiles — are
**not** required by any project document and are not listed as obligations here."*

So they are not listed here either. **Absent by choice, not oversight.** Adding a
required field to this contract is a decision and needs a decision-log entry.

## Required — every field traceable to a document

| Field | Content | Source | Phase |
|---|---|---|---|
| `artifact_path` | The compiled `.hef` | `[PRD 4.7, 5.3]` | M1 (stock), M6 (custom) |
| `input_width_px`, `input_height_px` | 640×640 baseline, **subject to OD-04** | `[PRD 2.2]`, `[ARCH Models]` | M1, M6 |
| `nms_location` | `on_device` \| `host_hailofilter`. Moves 1–3 ms of CPU: *"check which you are running before you attribute a latency spike to something else"* | `[PRD 5.2]` | M1 |
| `class_names` | Surveillance: COCO 0 person, 2 car, 3 motorcycle, 5 bus, 7 truck. Counter-UAV: single class `uav` ([0009](../docs/decisions/0009-counter-uav-single-class.md)) | `[ARCH Models]`, `[Team 2026-09-07]` | M1, M6 |
| `sustained_fps_aggregate` | Sustained FPS on the Hailo-8L, stated as **aggregate, not per camera** | `[PRD 1.5, 4.2]` | M1, M6 |
| `quantisation` | Accuracy verified **after** INT8 PTQ, small-object regime explicitly covered | `[PRD 5.3]` | M6 |
| `known_limitations` | Especially small-object behaviour after quantisation | `[PRD 5.3]` | M6 |

## PROVISIONAL / OPEN

| Field | Why it exists | Status |
|---|---|---|
| `artifact_version` | The pipeline needs to name what it is running | 🔴 **OPEN** — no versioning or naming convention exists in any document (Doc 2 §5.6). Free text until one is agreed |
| `architecture`, `licence` | [0013](../docs/decisions/0013-yolov8-licence-deferred.md): AGPL-3.0 is deferred, not eliminated. A one-line licence note per architecture makes the eventual decision a lookup rather than archaeology | 🟡 PROVISIONAL |
| `sha256` | Build identity, needed for the M7 frozen stack `[PRD 4.8]` | 🟡 PROVISIONAL |
| `metric_name`, thresholds | 🔴 **OPEN — OD-B3.** No document names an accuracy metric, threshold or held-out test set, so none is hard-coded. *"Person B cannot currently define done."* | 🔴 OPEN |

## Acceptance gate

🔴 **OPEN.** [Document 2 §6.2]: *"No acceptance gate is defined for Person A to
accept or reject a delivered model."* Integration is therefore a **reviewed human
decision**, not an automated check. `pod_contracts.MODEL_ACCEPTANCE_GATE` is the
string `"OPEN"` so the gap is visible in code, not only in a document. It should be
agreed alongside the metric in OD-B3.

## Hard constraints on any artifact

- **INT8 only. No FP16 fallback, no CUDA** `[PRD 5.1]`. *"Any model that does not
  survive post-training quantisation simply cannot run here."*
- Verify accuracy **after** quantisation, not before `[PRD 5.3]`. Small-object
  detection is the regime most sensitive to quantisation loss and small distant UAVs
  are exactly the hard case.
- The `.hef` must load through HailoRT via the `hailonet` GStreamer element
  `[PRD 5.1, 5.2]`.
- `.hef` files are **not committed** (see `.gitignore`). The manifest is committed;
  the artifact is delivered out of band.

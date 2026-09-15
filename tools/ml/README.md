# tools/ml — Person B's ML engineering foundation

**Owner:** Person B (Raghava) · **Status:** pre-dataset infrastructure (this pass),
not a trained model, not a real dataset. Peer of `tools/camera_bench/` and
`tools/calibration/` (Person C) under the same rationale as
[decision 0024](../../docs/decisions/0024-camera-validation-tooling-boundaries.md):
dev/build-time tooling that is not one of the seven `[PRD 2.3]` modules, must stay
importable with no camera/Pi/Hailo hardware, and is never imported by `src/pod_*`.

Stdlib only — no numpy, OpenCV or Pillow. The dev environment for this project does
not carry the `vision` extra, and nothing in this pass needs real pixel decoding.

## Layout

```
tools/ml/
    dataset/      representation, validation, manifest/splits, class schema,
                  pixels-on-target size analysis, a small CLI
    evaluation/   ground-truth/prediction matching, precision/recall, IoU, reports
    artifacts/    validation, checksumming and JSON I/O for
                  pod_contracts.ModelArtifactMetadata
    mock/         Detector protocol + a deterministic MockDetector
```

## Dataset representation

`tools.ml.dataset.types.DatasetSample` is this tool's own normalized shape — **not**
a CVAT, COCO or YOLO export. OD-B2 (dataset spec: size, splits, scenarios, quality
bar, versioning, hard-negative taxonomy) is OPEN, so no final storage format is
assumed. `tools.ml.dataset.loader` reads it from a JSONL interchange format, one
record per line (the same shape convention as `fixtures/replay/*.jsonl`):

```json
{"sample_id": "img_0001", "image_path": "images/img_0001.jpg",
 "image_width_px": 1456, "image_height_px": 1088,
 "annotations": [{"class_id": 0, "class_name": "uav",
                   "x_px": 10.0, "y_px": 20.0, "w_px": 30.0, "h_px": 15.0}],
 "split": "train", "dataset_id": "public-v0", "source": "roboflow:example"}
```

`annotations: []` is a deliberate hard-negative image (the standard object-detection
convention — no special class is invented for it, per
[decision 0009](../../docs/decisions/0009-counter-uav-single-class.md)). A record
with no `annotations` key at all is "missing annotation" and is reported, never
guessed. An adapter from a real CVAT export is future work once OD-B2 settles.

Bounding boxes reuse `pod_contracts.BBox` (pixels, top-left origin) for the geometry
value itself, but `DatasetSample`/`Annotation` are local to `tools.ml` — the same
split decision 0024 draws between `CalibrationBundle` and `pod_config.CameraIntrinsics`:
at-rest dataset-engineering data is not a cross-module runtime message.

## Validation workflow

`tools.ml.dataset.validate_dataset_file(path, class_schema)` loads and validates in
one pass, returning a structured `ValidationResult` (never just printed text). It
catches: missing/unreadable images (a stdlib PNG/JPEG header sniffer —
`image_probe.py` — no OpenCV needed), invalid/out-of-bounds/zero-dimension boxes,
malformed or missing annotation records, unknown classes, duplicate sample ids,
declared-vs-actual image dimension mismatches, train/val/test leakage (by image path
*and* by sample id), and empty datasets/splits.

CLI: `python -m tools.ml.dataset.cli validate DATASET.jsonl --classes uav` (exit 0 if
valid, 1 otherwise; prints per-code counts and every issue).

## Manifest / split workflow

`build_manifest(samples, dataset_id=..., version=...)` answers "exactly what samples
were used for this experiment?" with stable, byte-deterministic JSON.

`assign_splits(samples, ratios, seed=...)` assigns each sample to a split
deterministically via a hash of `(seed, sample_id)` — no `random`, no RNG state to
serialize, stable as the dataset grows (existing samples never move when new ones are
added, which is exactly what makes an accidental re-split's leakage visible instead
of silent). **`ratios` has no default** — the split ratio is a project decision that
has not been made (OD-B2); you must state what you used.

CLI: `python -m tools.ml.dataset.cli manifest DATASET.jsonl --dataset-id ID --version V --out manifest.json`

## Pixels-on-target / size analysis

`tools.ml.dataset.size_analysis` computes per-annotation width/height/area/
area-fraction (`compute_target_sizes`), summary statistics (`summarize_distribution`),
and lets a caller bucket targets by any size field with **caller-supplied**
boundaries (`bucket_by_size`) — no small/medium/large convention is hard-coded. This
is measurement machinery for OD-B3 (the pixels-on-target floor,
[decision 0014](../../docs/decisions/0014-public-dataset-training-now.md)), not the
floor itself.

## Evaluation workflow

`tools.ml.evaluation.evaluate_image(ground_truth, predictions, iou_threshold=...)`
greedily matches predictions to ground truth (highest confidence first, standard
VOC/COCO-style matching) and returns counts, precision, recall and mean matched IoU.
`iou_threshold` has no default — it is an evaluation-methodology choice this project
has not made. Precision/recall are `None` (not a fabricated `0.0`) when their
denominator is zero. `build_report(...)` aggregates per-image summaries into a
deterministic, JSON-serializable `EvaluationReport` for future experiment tracking;
`generated_at` is caller-supplied, never read from the clock internally.

There is **no acceptance threshold** anywhere in this module — OD-B3 is OPEN.

## Mock detector usage

```
Frame (FrameMeta)  ->  Detector  ->  Detection[]  (pod_contracts.Detection)
```

`tools.ml.mock.MockDetector` is a deterministic, scriptable stand-in for a real Hailo
detector: `schedule: {frame_seq: (Detection, ...)}` controls exactly which frames
carry a target, with no model and no hardware. It stops at the pre-tracking seam on
purpose — `pod_contracts.Detection` carries no track identity, and ByteTrack is not
implemented here (that is the real `hailotracker` GStreamer element,
`src/pod_perception/pipeline.py`, not Person B's first slice). Composing its output
into a `TrackedObject`/`TrackFrame` for a downstream test is the caller's job — see
`tests/unit/test_ml_mock_detector.py` for the pattern, and
`simulation.mocks.make_track_frame` for the existing full-mock alternative.

## Model artifact handoff

Builds only on the existing `pod_contracts.ModelArtifactMetadata` /
`QuantisationEvidence` — **no new contract**. `pod_contracts.codec.to_dict`/
`to_json_line` already serialize it generically (they dispatch on
`dataclasses.is_dataclass`); `tools.ml.artifacts.codec.artifact_metadata_from_dict`
adds the missing decode direction, kept here rather than in `pod_contracts` because
nothing in `src/pod_*` reads a manifest file yet (`pod_perception.build_pipeline`
takes a bare `model_hef_path: str`) — this is tooling-internal, not a cross-module
contract gap.

`tools.ml.artifacts.validate_artifact_metadata` checks only what
[`schemas/model_artifact.md`](../../schemas/model_artifact.md) supports: field
presence, positive dimensions, no duplicate/empty class names, a well-formed sha256
if present. It mirrors `tools.calibration.CalibrationBundle`'s
`validate()`/`hard_problems()` pattern — a `"note:"`-prefixed line is advisory. There
is deliberately **no accuracy/acceptance gate**:
`pod_contracts.MODEL_ACCEPTANCE_GATE` is the string `"OPEN"`, and integration stays a
reviewed human decision.

`tools.ml.artifacts.compute_sha256` / `verify_sha256` fill and check the manifest's
`sha256` field from an actual artifact file.

## What is IMPLEMENTED NOW

- Dataset representation, deterministic validation, manifest + hash-based splitting
- Pixels-on-target measurement machinery (no floor)
- Ground-truth/prediction matching, precision/recall/IoU, deterministic reports (no
  acceptance threshold)
- A deterministic `Detector` seam and `MockDetector`
- Structural validation, checksumming and JSON (de)serialization for
  `ModelArtifactMetadata`

## What REQUIRES REAL DATA

- Any actual dataset content, class balance, or scenario coverage (OD-B2)
- A real split ratio (this pass only builds the mechanism)
- Real evaluation numbers, and therefore a real precision/recall/mAP reading
- Real pixels-on-target measurements (needs the downscale/recall experiment
  [decision 0014](../../docs/decisions/0014-public-dataset-training-now.md) describes)

## What REQUIRES HARDWARE VALIDATION

- `sustained_fps_aggregate` in a real `ModelArtifactMetadata` (Hailo-8L measurement)
- Real image decoding at scale (numpy/OpenCV/Pillow — deliberately not added this
  pass; add as a lazy/optional dependency, matching `tools/camera_bench`'s
  `picamera2` pattern, when training actually starts)
- Post-quantisation accuracy evidence (`QuantisationEvidence`) — INT8, on-device

## What REQUIRES AN ARCHITECTURE DECISION

- OD-B2: dataset spec (size, splits, scenarios, quality bar, versioning, hard-negative
  taxonomy)
- OD-B3: model evaluation criteria and the pixels-on-target floor — schedule-critical,
  gates OD-19 (flight lens)
- OD-B4: architecture selection across model candidates
- OD-21: public-dataset training programme detail
- A final annotation-export format, once CVAT output is actually produced
  ([decision 0005](../../docs/decisions/0005-annotation-tool-cvat.md))

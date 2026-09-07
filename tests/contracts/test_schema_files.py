"""The JSON Schema files and the Python dataclasses must not drift apart.

[PRD 5.5] warns about exactly this failure for the Python/Kotlin telemetry mirror:
"the wire schema now has two definitions... treat any change as touching both, or
they will diverge." The JSON schemas are a third definition, so they get a test.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from pod_contracts import BBox, Detection, FrameMeta, TelemetryFrame, TrackedObject

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name", ["detection.schema.json", "telemetry.schema.json", "model_artifact.schema.json"]
)
def test_schema_is_valid_json_with_an_id(name: str) -> None:
    schema = _load(name)
    assert schema["$id"], f"{name} needs a stable $id"
    assert schema["description"], f"{name} needs a description saying who consumes it"


def test_detection_schema_matches_the_dataclasses() -> None:
    schema = _load("detection.schema.json")
    frame_props = set(schema["properties"]["frame"]["properties"])
    assert frame_props == {f.name for f in dataclasses.fields(FrameMeta)}

    track_props = set(schema["properties"]["tracks"]["items"]["properties"])
    assert track_props == {f.name for f in dataclasses.fields(TrackedObject)}

    det = schema["properties"]["tracks"]["items"]["properties"]["detection"]
    assert set(det["properties"]) == {f.name for f in dataclasses.fields(Detection)}
    assert set(det["properties"]["bbox"]["properties"]) == {
        f.name for f in dataclasses.fields(BBox)
    }


def test_detection_schema_requires_the_stamp() -> None:
    required = set(_load("detection.schema.json")["properties"]["frame"]["required"])
    assert {"capture_ts_ns", "frame_seq"} <= required


def test_telemetry_schema_matches_the_dataclass() -> None:
    schema = _load("telemetry.schema.json")
    assert set(schema["properties"]) == {f.name for f in dataclasses.fields(TelemetryFrame)}
    assert {"capture_ts_ns", "frame_seq"} <= set(schema["required"])

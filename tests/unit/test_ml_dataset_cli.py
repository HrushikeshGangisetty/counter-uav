"""tools.ml.dataset.cli: the callable command-line entry point."""

from __future__ import annotations

import json
import struct

from tools.ml.dataset.cli import main

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _png_bytes(width: int, height: int) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return _PNG_SIG + struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"


def _write_dataset(tmp_path, records) -> str:
    path = tmp_path / "ds.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return str(path)


def test_validate_returns_zero_for_a_clean_dataset(tmp_path, capsys) -> None:
    (tmp_path / "s1.png").write_bytes(_png_bytes(10, 10))
    ds = _write_dataset(
        tmp_path,
        [
            {
                "sample_id": "s1",
                "image_path": "s1.png",
                "image_width_px": 10,
                "image_height_px": 10,
                "annotations": [],
            }
        ],
    )
    code = main(["validate", ds, "--classes", "uav"])
    assert code == 0
    assert "0 issue(s)" in capsys.readouterr().out


def test_validate_returns_one_for_a_broken_dataset(tmp_path, capsys) -> None:
    ds = _write_dataset(
        tmp_path,
        [
            {
                "sample_id": "s1",
                "image_path": "missing.png",
                "image_width_px": 10,
                "image_height_px": 10,
                "annotations": [],
            }
        ],
    )
    code = main(["validate", ds, "--classes", "uav"])
    assert code == 1
    out = capsys.readouterr().out
    assert "missing_image" in out


def test_manifest_writes_output_file(tmp_path, capsys) -> None:
    (tmp_path / "s1.png").write_bytes(_png_bytes(10, 10))
    ds = _write_dataset(
        tmp_path,
        [
            {
                "sample_id": "s1",
                "image_path": "s1.png",
                "image_width_px": 10,
                "image_height_px": 10,
                "annotations": [],
                "split": "train",
            }
        ],
    )
    out_path = tmp_path / "manifest.json"
    code = main(["manifest", ds, "--dataset-id", "ds1", "--version", "v1", "--out", str(out_path)])
    assert code == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert data["dataset_id"] == "ds1"
    assert len(data["entries"]) == 1

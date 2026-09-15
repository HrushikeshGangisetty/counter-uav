"""tools.ml.dataset.image_probe: stdlib-only PNG/JPEG header dimension sniffing."""

from __future__ import annotations

import struct

from tools.ml.dataset.image_probe import ImageFormat, probe_image

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _png_bytes(width: int, height: int) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return _PNG_SIG + struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"


def _jpeg_bytes(width: int, height: int) -> bytes:
    comp = bytes([1, 0x11, 0])
    payload = bytes([8]) + struct.pack(">HH", height, width) + bytes([1]) + comp
    sof = b"\xff\xc0" + struct.pack(">H", len(payload) + 2) + payload
    return b"\xff\xd8" + sof + b"\xff\xd9"


def test_valid_png_reports_dimensions(tmp_path) -> None:
    path = tmp_path / "a.png"
    path.write_bytes(_png_bytes(1456, 1088))
    result = probe_image(path)
    assert result.format is ImageFormat.PNG
    assert (result.width_px, result.height_px) == (1456, 1088)
    assert result.corrupt is False


def test_valid_jpeg_reports_dimensions(tmp_path) -> None:
    path = tmp_path / "a.jpg"
    path.write_bytes(_jpeg_bytes(640, 480))
    result = probe_image(path)
    assert result.format is ImageFormat.JPEG
    assert (result.width_px, result.height_px) == (640, 480)
    assert result.corrupt is False


def test_truncated_png_is_corrupt(tmp_path) -> None:
    path = tmp_path / "bad.png"
    path.write_bytes(_PNG_SIG + b"\x00\x00")  # signature present, IHDR missing
    result = probe_image(path)
    assert result.format is ImageFormat.PNG
    assert result.corrupt is True
    assert result.width_px is None


def test_empty_file_is_corrupt(tmp_path) -> None:
    path = tmp_path / "empty.png"
    path.write_bytes(b"")
    result = probe_image(path)
    assert result.format is ImageFormat.UNKNOWN
    assert result.corrupt is True


def test_unrecognized_format_is_not_corrupt(tmp_path) -> None:
    path = tmp_path / "a.bmp"
    path.write_bytes(b"BM not really a bitmap but has some bytes")
    result = probe_image(path)
    assert result.format is ImageFormat.UNKNOWN
    assert result.corrupt is False
    assert result.width_px is None


def test_missing_path_is_corrupt_not_a_crash(tmp_path) -> None:
    result = probe_image(tmp_path / "does_not_exist.png")
    assert result.format is ImageFormat.UNKNOWN
    assert result.corrupt is True


def test_zero_dimension_png_ihdr_is_treated_as_corrupt(tmp_path) -> None:
    path = tmp_path / "zero.png"
    path.write_bytes(_png_bytes(0, 100))
    result = probe_image(path)
    assert result.corrupt is True

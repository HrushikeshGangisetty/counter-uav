"""Read an image's pixel dimensions from its file header, stdlib only.

No numpy, no Pillow, no OpenCV: the dev environment for this project does not carry
the ``vision`` extra (no ``cv2``), and dataset *validation* --- checking that an
image exists, is readable and that its declared width/height match what is on disk
--- does not need real pixel decoding, only the header. Supports PNG and baseline/
progressive JPEG, the two formats CVAT and Roboflow exports commonly use. An
unrecognized format is reported as such, never guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

#: Image headers are always well within the first 64 KiB, even with a large EXIF or
#: ICC-profile block ahead of the JPEG SOF marker. A worst-case profile could exceed
#: this, in which case the format is JPEG-recognized but dimensions come back
#: unavailable (not corrupt) --- see ``probe_image``.
_PROBE_READ_BYTES = 65536

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SOI = b"\xff\xd8"
#: SOF0-SOF15 marker bytes that carry frame dimensions, excluding DHT (0xC4), JPG
#: (0xC8, reserved) and DAC (0xCC), which share the 0xC0-0xCF range but are not SOF.
_JPEG_SOF_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)


class ImageFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ImageProbeResult:
    """Result of probing one image file's header.

    ``corrupt`` is only ever True when the magic bytes identified a known format but
    dimensions could not be parsed out of it (a truncated or malformed file, or an
    empty/unreadable file). An unrecognized format is ``UNKNOWN`` with
    ``corrupt=False``: this tool does not claim to support it, which is not the same
    as the file being broken.
    """

    format: ImageFormat
    width_px: int | None
    height_px: int | None
    corrupt: bool


def _parse_png(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[12:16] != b"IHDR":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        return None
    return (width, height)


def _parse_jpeg(data: bytes) -> tuple[int, int] | None:
    n = len(data)
    i = 2  # past the SOI marker
    while i + 1 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xFF:  # fill byte between markers
            i += 1
            continue
        if marker in (0x01,) or 0xD0 <= marker <= 0xD7:  # markers with no payload
            i += 2
            continue
        if marker == 0xD9:  # EOI
            return None
        if i + 4 > n:
            return None
        seg_len = (data[i + 2] << 8) | data[i + 3]
        if marker in _JPEG_SOF_MARKERS:
            if i + 9 > n or seg_len < 7:
                return None
            height = (data[i + 5] << 8) | data[i + 6]
            width = (data[i + 7] << 8) | data[i + 8]
            if width <= 0 or height <= 0:
                return None
            return (width, height)
        if seg_len < 2:
            return None
        i += 2 + seg_len
    return None


def probe_image(path: str | Path) -> ImageProbeResult:
    """Probe one image file. Never raises: an unreadable path comes back ``UNKNOWN``
    and ``corrupt=True``, matching "the file exists but cannot be read"."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(_PROBE_READ_BYTES)
    except OSError:
        return ImageProbeResult(ImageFormat.UNKNOWN, None, None, corrupt=True)

    if not data:
        return ImageProbeResult(ImageFormat.UNKNOWN, None, None, corrupt=True)

    if data[:8] == _PNG_SIGNATURE:
        dims = _parse_png(data)
        if dims is None:
            return ImageProbeResult(ImageFormat.PNG, None, None, corrupt=True)
        return ImageProbeResult(ImageFormat.PNG, dims[0], dims[1], corrupt=False)

    if data[:2] == _JPEG_SOI:
        dims = _parse_jpeg(data)
        if dims is None:
            # Could be corrupt, or the SOF marker simply lies past _PROBE_READ_BYTES
            # (a very large embedded profile). Either way dimensions are unavailable,
            # not necessarily corrupt -- callers should treat this as "cannot verify".
            return ImageProbeResult(ImageFormat.JPEG, None, None, corrupt=False)
        return ImageProbeResult(ImageFormat.JPEG, dims[0], dims[1], corrupt=False)

    return ImageProbeResult(ImageFormat.UNKNOWN, None, None, corrupt=False)

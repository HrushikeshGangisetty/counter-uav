"""SHA-256 checksums for model artifact files. Stdlib only."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


def compute_sha256(path: str | Path) -> str:
    """Hex-digest SHA-256 of a file's contents, streamed so a multi-MB ``.hef``
    does not need to fit in memory at once."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: str | Path, expected: str) -> bool:
    return compute_sha256(path) == expected.lower()

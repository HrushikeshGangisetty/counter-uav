"""Dataset manifest generation and deterministic train/val/test splitting.

A manifest answers "exactly what samples were used for this experiment?" --- stable
ordering, deterministic JSON, no ambiguity about what is in it.

Splitting is a hash of ``(seed, sample_id)``, not ``random``: the same seed always
produces the same assignment on any machine, with no RNG state to serialize or drift
across Python versions. Neither the split ratio nor the split strategy is decided by
any project document (OD-B2 is OPEN), so ``ratios`` is a required argument here, not
a default --- a caller must state what it used.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .types import DatasetSample


class SplitError(ValueError):
    """Split ratios do not form a valid partition."""


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    sample_id: str
    split: str
    image_path: str
    image_width_px: int
    image_height_px: int
    annotation_count: int
    dataset_id: str = ""
    source: str = ""


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """The full record of what samples went into one dataset version."""

    dataset_id: str
    version: str
    entries: tuple[ManifestEntry, ...]

    def sample_ids(self) -> tuple[str, ...]:
        return tuple(e.sample_id for e in self.entries)

    def split_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.entries:
            counts[e.split] = counts.get(e.split, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "entries": [
                {
                    "sample_id": e.sample_id,
                    "split": e.split,
                    "image_path": e.image_path,
                    "image_width_px": e.image_width_px,
                    "image_height_px": e.image_height_px,
                    "annotation_count": e.annotation_count,
                    "dataset_id": e.dataset_id,
                    "source": e.source,
                }
                # Stable ordering: sorted by sample_id, independent of input order,
                # so the same sample set always serializes identically.
                for e in sorted(self.entries, key=lambda e: e.sample_id)
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def build_manifest(
    samples: Sequence[DatasetSample], *, dataset_id: str, version: str
) -> DatasetManifest:
    entries = tuple(
        ManifestEntry(
            sample_id=s.sample_id,
            split=s.split,
            image_path=s.image_path,
            image_width_px=s.image_width_px,
            image_height_px=s.image_height_px,
            annotation_count=len(s.annotations),
            dataset_id=s.dataset_id,
            source=s.source,
        )
        for s in sorted(samples, key=lambda s: s.sample_id)
    )
    return DatasetManifest(dataset_id=dataset_id, version=version, entries=entries)


def save_manifest(manifest: DatasetManifest, path: str | Path) -> None:
    Path(path).write_text(manifest.to_json(), encoding="utf-8", newline="\n")


def load_manifest(path: str | Path) -> DatasetManifest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = tuple(
        ManifestEntry(
            sample_id=str(e["sample_id"]),
            split=str(e["split"]),
            image_path=str(e["image_path"]),
            image_width_px=int(e["image_width_px"]),
            image_height_px=int(e["image_height_px"]),
            annotation_count=int(e["annotation_count"]),
            dataset_id=str(e.get("dataset_id", "")),
            source=str(e.get("source", "")),
        )
        for e in data["entries"]
    )
    return DatasetManifest(
        dataset_id=str(data["dataset_id"]), version=str(data["version"]), entries=entries
    )


def _split_bucket(seed: int, sample_id: str) -> float:
    """A deterministic value in [0, 1) for one (seed, sample_id) pair."""
    digest = hashlib.sha256(f"{seed}:{sample_id}".encode()).digest()
    as_int = int.from_bytes(digest[:8], "big")
    return as_int / 2**64


def assign_splits(
    samples: Sequence[DatasetSample], ratios: Mapping[str, float], *, seed: int = 0
) -> tuple[DatasetSample, ...]:
    """Deterministically assign each sample to a split named in ``ratios``.

    ``ratios`` values must be positive and sum to 1.0 (within floating-point
    tolerance) --- there is no built-in default split, by design: the ratio is a
    project decision that has not been made (OD-B2). Assignment is a stable hash of
    ``(seed, sample_id)``, so re-running with the same seed and the same sample_ids
    reproduces the same split even if the dataset grows, which is what makes
    leakage from a later re-split visible rather than silent.
    """
    if not ratios:
        raise SplitError("ratios must name at least one split")
    if any(r <= 0 for r in ratios.values()):
        raise SplitError(f"all split ratios must be positive: {ratios}")
    total = sum(ratios.values())
    if abs(total - 1.0) > 1e-9:
        raise SplitError(f"split ratios must sum to 1.0, got {total} ({ratios})")

    # Fixed iteration order so the cumulative boundaries -- and therefore every
    # sample's assignment -- do not depend on dict ordering the caller happened to use.
    names = sorted(ratios)
    boundaries: list[tuple[str, float]] = []
    cumulative = 0.0
    for name in names:
        cumulative += ratios[name]
        boundaries.append((name, cumulative))

    out = []
    for sample in samples:
        bucket = _split_bucket(seed, sample.sample_id)
        split = boundaries[-1][0]
        for name, upper in boundaries:
            if bucket < upper:
                split = name
                break
        out.append(
            DatasetSample(
                sample_id=sample.sample_id,
                image_path=sample.image_path,
                image_width_px=sample.image_width_px,
                image_height_px=sample.image_height_px,
                annotations=sample.annotations,
                split=split,
                dataset_id=sample.dataset_id,
                source=sample.source,
            )
        )
    return tuple(out)

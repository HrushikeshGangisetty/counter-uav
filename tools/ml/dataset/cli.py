"""Command-line entry point for dataset validation and manifest generation.

python -m tools.ml.dataset.cli validate DATASET.jsonl [--classes uav,...]
    [--image-root DIR] [--expect-split train,val,test] [--no-check-images]
python -m tools.ml.dataset.cli manifest DATASET.jsonl --dataset-id ID
    --version V --out manifest.json
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .loader import load_dataset_jsonl
from .manifest import build_manifest, save_manifest
from .schema import ClassSchema
from .validate import validate_dataset_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tools.ml.dataset", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate_p = sub.add_parser("validate", help="Validate a dataset JSONL file")
    validate_p.add_argument("dataset", help="Path to the dataset JSONL file")
    validate_p.add_argument(
        "--classes", required=True, help="Comma-separated class names, in class_id order"
    )
    validate_p.add_argument("--image-root", default=None, help="Base directory for image_path")
    validate_p.add_argument(
        "--expect-split", default="", help="Comma-separated split names that must be non-empty"
    )
    validate_p.add_argument(
        "--no-check-images", action="store_true", help="Skip filesystem checks on image files"
    )

    manifest_p = sub.add_parser("manifest", help="Build a manifest from a dataset JSONL file")
    manifest_p.add_argument("dataset", help="Path to the dataset JSONL file")
    manifest_p.add_argument("--dataset-id", required=True)
    manifest_p.add_argument("--version", required=True)
    manifest_p.add_argument("--out", required=True, help="Output manifest JSON path")

    return parser


def _run_validate(args: argparse.Namespace) -> int:
    class_schema = ClassSchema(tuple(c.strip() for c in args.classes.split(",") if c.strip()))
    expected_splits = tuple(s.strip() for s in args.expect_split.split(",") if s.strip())
    result = validate_dataset_file(
        args.dataset,
        class_schema,
        image_root=args.image_root,
        check_images=not args.no_check_images,
        expected_splits=expected_splits,
    )
    print(f"{result.sample_count} samples, {len(result.issues)} issue(s)")
    for code, count in sorted(result.counts_by_code().items()):
        print(f"  {code}: {count}")
    for issue in result.issues:
        where = f"[{issue.sample_id}] " if issue.sample_id else ""
        print(f"{issue.severity.value:7s} {issue.code:24s} {where}{issue.message}")
    return 0 if result.is_valid else 1


def _run_manifest(args: argparse.Namespace) -> int:
    samples = load_dataset_jsonl(args.dataset)
    manifest = build_manifest(samples, dataset_id=args.dataset_id, version=args.version)
    save_manifest(manifest, args.out)
    print(f"wrote {len(manifest.entries)} entries -> {args.out}")
    for split, count in sorted(manifest.split_counts().items()):
        print(f"  split {split or '(unassigned)'}: {count}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        return _run_validate(args)
    if args.command == "manifest":
        return _run_manifest(args)
    parser.error(f"unknown command {args.command!r}")  # pragma: no cover - argparse enforces this
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

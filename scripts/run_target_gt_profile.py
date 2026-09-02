#!/usr/bin/env python3
"""Regenerate the Fintra 16.5 target-GT profile from the private OCR corpus."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.target_gt_analysis import analyze_target_archives, write_analysis_json
from fintra_ocr.target_selection import select_target_archive_pairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "analysis" / "target_gt_profile.json",
        help="profile JSON output path",
    )
    parser.add_argument("--representatives", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.representatives <= 0:
        raise SystemExit("--representatives must be positive")
    try:
        archive_groups = discover_archives()
    except NotADirectoryError as error:
        raise SystemExit(
            "Private OCR corpus not found. Expected OCR/Training and OCR/Validation "
            f"under {PROJECT_ROOT}. Missing: {error}"
        ) from error
    selected = select_target_archive_pairs(archive_groups)
    result = analyze_target_archives(selected, representatives_per_type=args.representatives)
    write_analysis_json(result, args.output)

    print(f"analysis_version={result['analysis_version']}")
    print(f"document_count={result['document_count']}")
    for document_type, summary in result["document_types"].items():
        print(
            f"{document_type}: documents={summary['document_count']} "
            f"malformed={summary['malformed_records']}"
        )
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


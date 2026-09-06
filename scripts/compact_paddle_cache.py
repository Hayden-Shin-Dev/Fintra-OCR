"""Compact an existing Paddle cache without rerunning OCR."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.ocr.adapter import OCRResult


def compact(source_root: Path, output_root: Path) -> dict[str, int]:
    count = 0
    for source_case in sorted(item for item in (source_root / "cases").iterdir() if item.is_dir()):
        source_json = source_case / "outputs" / "recognition" / "paddle.json"
        source_raw = source_case / "outputs" / "raw" / "paddle_raw.json"
        if not source_json.is_file() or not source_raw.is_file():
            continue
        result = OCRResult.from_json(source_json, preserve_raw=False)
        destination = output_root / "cases" / source_case.name
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("case_manifest.json", "semantic_gold_fields.json"):
            shutil.copy2(source_case / name, destination / name)
        raw_dir = destination / "outputs" / "raw"
        recognition_dir = destination / "outputs" / "recognition"
        raw_dir.mkdir(parents=True, exist_ok=True)
        recognition_dir.mkdir(parents=True, exist_ok=True)
        compressed = raw_dir / "paddle_raw.json.gz"
        with source_raw.open("rb") as source, gzip.open(compressed, "wb") as target:
            shutil.copyfileobj(source, target)
        compacted = OCRResult(
            result.document_id, result.document_type, result.source_file, result.regions,
            raw_output=None, raw_output_path=str(compressed), runtime=result.runtime,
            metadata={**result.metadata, "raw_compression": "gzip", "raw_source_preserved": True},
        )
        (recognition_dir / "paddle.json").write_text(
            json.dumps(compacted.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        count += 1
    summary = {"compacted": count, "output_root": str(output_root.resolve())}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "compact_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    compact(args.source_root, args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

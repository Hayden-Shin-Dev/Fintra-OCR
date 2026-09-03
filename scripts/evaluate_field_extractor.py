"""Run a field-level before/after regression over stored OCR JSON results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintra_ocr.field_evaluation import evaluate_prediction_rows, load_prediction_rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate extractor changes without rerunning or modifying OCR/model assets"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing one stored OCR result JSON per document",
    )
    parser.add_argument("--output", required=True, help="Output evaluation JSON path")
    args = parser.parse_args()

    rows = load_prediction_rows(args.input_dir)
    report = evaluate_prediction_rows(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "documents": report["document_count"],
        "oracle_proxy_fields": report["oracle_proxy_field_count"],
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

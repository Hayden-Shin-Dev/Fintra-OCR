"""Check that an existing evaluation CSV and JSON summary agree exactly."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = list(csv.DictReader(args.csv.open(encoding="utf-8-sig", newline="")))
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    counts = Counter(row.get("status") for row in rows)
    overall = metrics.get("overall", {})
    checks = {
        "csv_row_count_matches_selection": len(rows) == int(metrics.get("selection", {}).get("rows", -1)),
        "csv_status_counts_match_summary": dict(counts) == dict(overall.get("status_counts", {})),
        "csv_applicable_matches_summary": sum(row.get("gt_status") == "available" for row in rows) == int(overall.get("applicable_gold", -1)),
        "csv_normalized_matches_match_summary": sum(row.get("status") in {"exact_match", "normalized_match"} for row in rows) == int(overall.get("normalized_matches", -1)),
        "csv_wrong_matches_summary": counts["wrong"] == int(overall.get("wrong", -1)),
        "csv_missing_matches_summary": counts["missing"] == int(overall.get("missing", -1)),
    }
    result = {
        "csv": str(args.csv),
        "metrics": str(args.metrics),
        "csv_rows": len(rows),
        "csv_status_counts": dict(counts),
        "summary_status_counts": overall.get("status_counts", {}),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "prediction_blind": False,
        "ocr_read": True,
        "extractor_read": True,
        "final_holdout_2_accessed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

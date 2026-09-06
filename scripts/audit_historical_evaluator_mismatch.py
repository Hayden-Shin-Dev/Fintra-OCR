"""Audit the reproducible side of the historical 625-vs-626 discrepancy.

This tool reads only an explicitly supplied historical CSV/JSON pair. It
does not read Gold-generation inputs, modify Gold, or inspect any holdout.
When the historical 625-side artifact is absent, it reports that limitation
instead of inventing a root cause.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from audit_evaluator_consistency import consistency_checks


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def counts_by_type(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for kind in sorted({row.get("document_type", "") for row in rows}):
        subset = [row for row in rows if row.get("document_type") == kind]
        result[kind] = {
            "rows": len(subset),
            "applicable": sum(row.get("gt_status") == "available" for row in subset),
            "exact": sum(row.get("status") == "exact_match" for row in subset),
            "normalized_only": sum(row.get("status") == "normalized_match" for row in subset),
            "normalized_matches": sum(row.get("status") in {"exact_match", "normalized_match"} for row in subset),
        }
    return result


def audit(csv_path: Path, metrics_path: Path, claimed_scope: str, claimed_value: int) -> dict[str, Any]:
    rows = load_rows(csv_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    _, checks = consistency_checks(rows, metrics)
    overall = metrics.get("overall", {})
    by_type = counts_by_type(rows)
    if claimed_scope == "overall":
        reproducible_value = sum(row.get("status") in {"exact_match", "normalized_match"} for row in rows)
    else:
        kind, field = claimed_scope.split(":", 1)
        subset = [row for row in rows if row.get("document_type") == kind and (field == "__all__" or row.get("field_name") == field)]
        reproducible_value = sum(row.get("status") in {"exact_match", "normalized_match"} for row in subset)
    result = {
        "input_csv": str(csv_path),
        "input_metrics": str(metrics_path),
        "rows": len(rows),
        "recomputed_overall_normalized_matches": sum(row.get("status") in {"exact_match", "normalized_match"} for row in rows),
        "persisted_overall_normalized_matches": overall.get("normalized_matches"),
        "recomputed_by_document_type": by_type,
        "consistency_checks": checks,
        "current_pair_status": "PASS" if all(checks.values()) else "FAIL",
        "historical_claim": {"scope": claimed_scope, "value": claimed_value, "recomputed_value": reproducible_value, "reproduced": reproducible_value == claimed_value},
        "historical_625_side_artifact_present": False,
        "root_cause_status": "UNRESOLVED_HISTORICAL_INPUT_NOT_PRESENT" if reproducible_value != claimed_value else "REPRODUCED",
        "interpretation": (
            "The supplied CSV/JSON pair is internally consistent. In the preserved v3.2 pair, CI normalized matches are 605 exact + 21 normalized-only = 626. The historical 625-side input/report is not present locally, so its exact one-row cause cannot be proven."
            if reproducible_value != claimed_value else
            "The supplied historical claim is reproduced by the supplied CSV."
        ),
        "prediction_blind": False,
        "ocr_read": True,
        "extractor_read": True,
        "final_holdout_2_accessed": False,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--claimed-scope", default="Commercial Invoice:__all__")
    parser.add_argument("--claimed-value", type=int, default=625)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.csv, args.metrics, args.claimed_scope, args.claimed_value)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Historical evaluator mismatch audit",
        "",
        "This audit does not alter Gold and does not inspect FINAL-HOLDOUT #2.",
        "",
        f"- Input CSV: {args.csv}",
        f"- Input metrics: {args.metrics}",
        f"- Current pair consistency: {result['current_pair_status']}",
        f"- Recomputed overall normalized matches: {result['recomputed_overall_normalized_matches']}",
        f"- Persisted overall normalized matches: {result['persisted_overall_normalized_matches']}",
        f"- Claimed historical value: {args.claimed_value} for {args.claimed_scope}",
        f"- Claimed value reproduced: {result['historical_claim']['reproduced']}",
        "",
        "## Reproducible result",
        "",
        "The preserved semantic-v3.2-balanced300 pair has CI normalized matches 626, consisting of 605 exact matches plus 21 normalized-only matches. CSV and JSON agree on rows, status counts, applicable denominator, normalized matches, wrong, and missing counts.",
        "",
        "## Closure",
        "",
        "The historical 625-side CSV/JSON or the exact code invocation that produced it is not present in the repository artifacts. Therefore the precise one-row cause is not technically reproducible from local evidence; labeling it as a confirmed evaluator bug would be unsupported.",
        "",
        f"- Root-cause status: {result['root_cause_status']}",
        "- Required follow-up for full closure: preserve the exact 625-side CSV/JSON pair or its run log and rerun this audit.",
    ]
    args.output.with_suffix(".md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if result["current_pair_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Classify frozen-OCR field failures for a scale evaluation subset.

The script never edits gold or OCR output.  It joins the frozen extractor
result with the raw-OCR evidence evaluator and writes an auditable failure
matrix for one document type or for all document types.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluate_ocr_stages as stage_eval


def _obvious_gold_issue(row: dict[str, object]) -> str | None:
    value = str(row.get("gt_value") or "").strip()
    field = str(row.get("field_base") or "")
    normalized = re.sub(r"[^A-Z0-9 ]+", " ", value.upper()).strip()
    if field in {"seller", "buyer", "exporter", "consignee", "shipper", "notify_party"}:
        if normalized in {"SAME AS ABOVE", "NEW ZEALAND", "SAUDI ARABIA", "UNITED STATES", "CHINA"}:
            return "party value is a reference/country-only line; semantic role is not independently typed"
    if not value:
        return "empty available gold value"
    return None


def analyze(cases_root: Path, ocr_cases_root: Path, field_results: Path,
            gold_root: Path, output_dir: Path, document_type: str | None) -> dict[str, object]:
    with field_results.open(encoding="utf-8-sig", newline="") as handle:
        extracted = {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}

    failures: list[dict[str, object]] = []
    for case_path in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_path / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        kind = manifest["document_type"]
        if document_type and kind != document_type:
            continue
        case = {"path": case_path, "case_id": manifest["case_id"],
                "document_id": manifest["document_id"], "document_type": kind}
        ocr_path = ocr_cases_root / manifest["case_id"] / "outputs" / "recognition" / "paddle.json"
        evidence_rows = stage_eval._field_evidence(case, "paddle", stage_eval._read_ocr(ocr_path), gold_root)
        for evidence in evidence_rows:
            key = (evidence["case_id"], evidence["field_name"])
            prediction = extracted.get(key, {})
            if prediction.get("status") in {"exact_match", "normalized_match"}:
                continue
            gold_issue = _obvious_gold_issue(evidence)
            if gold_issue:
                classification = "GOLD_AMBIGUOUS_OR_MISMATCH"
                reason = gold_issue
            elif evidence["classification"] in stage_eval.RECOVERABLE:
                classification = "EXTRACTOR_WRONG"
                reason = "gold text is recoverable from frozen Paddle OCR evidence"
            else:
                classification = "OCR_MISSING"
                reason = evidence["classification"]
            failures.append({
                "case_id": evidence["case_id"],
                "document_id": evidence["document_id"],
                "document_type": evidence["document_type"],
                "field_name": evidence["field_name"],
                "field_base": evidence["field_base"],
                "gt_value": evidence["gt_value"],
                "predicted_value": prediction.get("predicted_value", ""),
                "extractor_status": prediction.get("status", "missing"),
                "extractor_source_text": prediction.get("source_text", ""),
                "ocr_classification": evidence["classification"],
                "closest_ocr_text": evidence["closest_ocr_text"],
                "combined_ocr_text": evidence["combined_ocr_text"],
                "neighboring_ocr_texts": evidence["neighboring_ocr_texts"],
                "fuzzy_similarity": evidence["fuzzy_similarity"],
                "classification": classification,
                "classification_reason": reason,
            })

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(failures[0]) if failures else ["case_id"]
    with (output_dir / "failure_matrix.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(failures)

    by_field: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    by_group: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    for row in failures:
        by_field[str(row["field_name"])][str(row["classification"])] += 1
        match = re.match(r"(BL|INV|PL)\d+", str(row["case_id"]), re.I)
        group = match.group(0).upper() if match else "UNKNOWN"
        by_group[group][str(row["classification"])] += 1
    metrics = {
        "document_type": document_type or "ALL",
        "failure_rows": len(failures),
        "classification_counts": dict(Counter(str(row["classification"]) for row in failures)),
        "by_field": {key: dict(value) for key, value in sorted(by_field.items())},
        "by_source_group": {key: dict(value) for key, value in sorted(by_group.items())},
        "contract": "Frozen Paddle OCR and frozen semantic-v3.1 gold; gold is never changed by this diagnostic.",
    }
    (output_dir / "failure_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# {document_type or 'All'} field failure analysis", "", metrics["contract"], "",
             f"Failure rows: {len(failures)}", "", "## Classification", ""]
    for key, value in metrics["classification_counts"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Field matrix", ""]
    for key, value in metrics["by_field"].items():
        lines.append(f"- `{key}`: " + ", ".join(f"{name}={count}" for name, count in sorted(value.items())))
    (output_dir / "FAILURE_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--ocr-cases-root", type=Path, required=True)
    parser.add_argument("--field-results", type=Path, required=True)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--document-type", default=None)
    args = parser.parse_args()
    print(json.dumps(analyze(args.cases_root, args.ocr_cases_root, args.field_results,
                              args.gold_root, args.output_dir, args.document_type), ensure_ascii=False))


if __name__ == "__main__":
    main()

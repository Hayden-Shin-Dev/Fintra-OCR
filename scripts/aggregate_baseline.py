"""Aggregate per-case CPU reference metrics by document type and overall."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gt = sum(row["gt_regions"] for row in rows)
    predictions = sum(row["prediction_regions"] for row in rows)
    matched = sum(row["matched"] for row in rows)
    exact = sum(row["recognition_exact_matches"] for row in rows)
    normalized_exact = sum(row["normalized_exact_matches"] for row in rows)
    edit_sum = sum(row.get("edit_distance_sum", 0) for row in rows)
    edit_denominator = sum(row.get("edit_denominator", 0) for row in rows)
    macro_fields = [
        "detection_precision",
        "detection_recall",
        "detection_f1",
        "recognition_exact_accuracy_on_matched",
        "normalized_exact_accuracy_on_matched",
        "cer_on_matched",
        "end_to_end_exact_recall",
    ]
    return {
        "documents": len(rows),
        "gt_regions": gt,
        "prediction_regions": predictions,
        "matched": matched,
        "missed_gt": gt - matched,
        "false_positive_predictions": predictions - matched,
        "recognition_exact_matches": exact,
        "normalized_exact_matches": normalized_exact,
        "edit_distance_sum": edit_sum,
        "edit_denominator": edit_denominator,
        "micro_detection_precision": matched / predictions if predictions else 0.0,
        "micro_detection_recall": matched / gt if gt else 0.0,
        "micro_detection_f1": 2 * matched / (gt + predictions) if gt or predictions else 0.0,
        "micro_exact_accuracy_on_matched": exact / matched if matched else 0.0,
        "micro_normalized_exact_accuracy_on_matched": normalized_exact / matched if matched else 0.0,
        "micro_cer_on_matched": edit_sum / edit_denominator if edit_denominator else 0.0,
        "micro_end_to_end_exact_recall": exact / gt if gt else 0.0,
        "macro": {field: sum(row[field] for row in rows) / len(rows) for field in macro_fields},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    cases = []
    for case_dir in sorted(args.input_root.iterdir()):
        metrics_path = case_dir / "evaluation" / "metrics.json"
        if not metrics_path.is_file():
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        cases.append({"case_id": case_dir.name, "document_type": metrics["document_type"], "metrics": metrics})
    if not cases:
        raise RuntimeError("no evaluated cases found")

    by_type: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        by_type.setdefault(case["document_type"], []).append(case["metrics"])
    result = {
        "schema_version": "fintra-ocr-v2.aggregate.v1",
        "baseline_name": "AI-Hub original weights/code CPU reference baseline",
        "documents": [{"case_id": c["case_id"], "document_type": c["document_type"]} for c in cases],
        "by_document_type": {},
        "overall": {},
    }
    for threshold in ("0.5", "0.8"):
        result["by_document_type"][threshold] = {
            doc_type: _aggregate([case["metrics_by_iou_threshold"][threshold] for case in rows])
            for doc_type, rows in sorted(by_type.items())
        }
        result["overall"][threshold] = _aggregate([
            case["metrics"]["metrics_by_iou_threshold"][threshold] for case in cases
        ])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# AI-Hub original weights/code CPU reference baseline — 15-document smoke aggregate",
        "",
        "This aggregate uses one real AI-Hub Validation document selected from each CI/PL/B/L ZIP pair. It is a CPU reference result, not an official GPU baseline or official AI-Hub reproduced score.",
        "",
        "| Type | Docs | GT | Pred | Match@0.5 | Det F1 micro@0.5 | Exact@0.5 | CER@0.5 | Match@0.8 | Det F1 micro@0.8 | Exact@0.8 | CER@0.8 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for doc_type in sorted(by_type):
        a, b = result["by_document_type"]["0.5"][doc_type], result["by_document_type"]["0.8"][doc_type]
        lines.append(f"| {doc_type} | {a['documents']} | {a['gt_regions']} | {a['prediction_regions']} | {a['matched']} | {a['micro_detection_f1']:.6f} | {a['micro_exact_accuracy_on_matched']:.6f} | {a['micro_cer_on_matched']:.6f} | {b['matched']} | {b['micro_detection_f1']:.6f} | {b['micro_exact_accuracy_on_matched']:.6f} | {b['micro_cer_on_matched']:.6f} |")
    a, b = result["overall"]["0.5"], result["overall"]["0.8"]
    lines.append(f"| **Overall** | **{a['documents']}** | **{a['gt_regions']}** | **{a['prediction_regions']}** | **{a['matched']}** | **{a['micro_detection_f1']:.6f}** | **{a['micro_exact_accuracy_on_matched']:.6f}** | **{a['micro_cer_on_matched']:.6f}** | **{b['matched']}** | **{b['micro_detection_f1']:.6f}** | **{b['micro_exact_accuracy_on_matched']:.6f}** | **{b['micro_cer_on_matched']:.6f}** |")
    lines += ["", "Macro metrics are the arithmetic mean of per-document rates; micro metrics pool region counts and edit-distance totals."]
    (args.output_dir / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["overall"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

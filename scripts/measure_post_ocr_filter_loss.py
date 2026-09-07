"""Measure evidence lost between raw Paddle regions and extractor regions.

The report is diagnostic only.  It reads frozen OCR JSON, frozen Gold, and
the existing case annotations; it never changes any of those inputs and it
does not call OCR.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.extraction import production_engine
from fintra.ocr.adapter import OCRResult
from scripts import evaluate_ocr_stages as stages


def _case_paths(cases_root: Path, ocr_root: Path, gold_root: Path, gt_root: Path) -> list[dict[str, Any]]:
    cases = []
    for case_path in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_path / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        case_id = str(manifest["case_id"])
        ocr_path = ocr_root / case_id / "outputs" / "recognition" / "paddle.json"
        if not ocr_path.is_file():
            candidates = sorted((ocr_root / case_id / "outputs" / "recognition").glob("*.json"))
            if len(candidates) == 1:
                ocr_path = candidates[0]
        gt_dir = gt_root / case_id
        gt_path = gt_dir / "gt.json" if (gt_dir / "gt.json").is_file() else gt_dir / "source_annotation.json"
        gold_path = gold_root / case_id / "semantic_gold_fields.json"
        if not ocr_path.is_file() or not gt_path.is_file() or not gold_path.is_file():
            raise FileNotFoundError(f"missing inputs for {case_id}: OCR={ocr_path}, GT={gt_path}, Gold={gold_path}")
        cases.append({
            "path": case_path,
            "case_id": case_id,
            "document_id": str(manifest["document_id"]),
            "document_type": str(manifest["document_type"]),
            "ocr_path": ocr_path,
            "gt_path": gt_path,
            "gold_path": gold_path,
        })
    return cases


def _filtered_regions(ocr_path: Path, document_type: str) -> list[dict[str, Any]]:
    result = OCRResult.from_json(ocr_path, document_type=document_type, preserve_raw=False)
    return [
        {"index": region.index, "polygon": region.polygon, "box": region.bbox, "text": region.text, "confidence": region.confidence}
        for region in production_engine._regions(result)
    ]


def measure(cases_root: Path, ocr_root: Path, gold_root: Path, gt_root: Path, output: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in _case_paths(cases_root, ocr_root, gold_root, gt_root):
        gold = json.loads(case["gold_path"].read_text(encoding="utf-8"))
        raw = stages._read_ocr(case["ocr_path"])
        filtered = _filtered_regions(case["ocr_path"], case["document_type"])
        raw_evidence = stages._field_evidence(case, "paddle_raw", raw, gold_fields=gold)
        filtered_evidence = stages._field_evidence(case, "paddle_filtered", filtered, gold_fields=gold)
        by_field = {item["field_name"]: item for item in filtered_evidence}
        for raw_item in raw_evidence:
            filtered_item = by_field[raw_item["field_name"]]
            raw_recoverable = raw_item["classification"] in stages.RECOVERABLE
            filtered_recoverable = filtered_item["classification"] in stages.RECOVERABLE
            status = (
                "POST_OCR_FILTER_LOSS" if raw_recoverable and not filtered_recoverable
                else "RETAINED_RECOVERABLE" if filtered_recoverable
                else "RAW_UNRECOVERABLE"
            )
            rows.append({
                "case_id": case["case_id"],
                "document_id": case["document_id"],
                "document_type": case["document_type"],
                "field_name": raw_item["field_name"],
                "field_base": raw_item["field_base"],
                "gt_value": raw_item["gt_value"],
                "raw_classification": raw_item["classification"],
                "filtered_classification": filtered_item["classification"],
                "raw_candidate_count": raw_item["candidate_count"],
                "filtered_candidate_count": filtered_item["candidate_count"],
                "raw_neighboring_ocr_texts": raw_item["neighboring_ocr_texts"],
                "filtered_neighboring_ocr_texts": filtered_item["neighboring_ocr_texts"],
                "status": status,
            })

    def aggregate(group: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(row["status"] for row in group)
        return {
            "applicable": len(group),
            "raw_recoverable": counts["POST_OCR_FILTER_LOSS"] + counts["RETAINED_RECOVERABLE"],
            "post_ocr_filter_loss": counts["POST_OCR_FILTER_LOSS"],
            "retained_recoverable": counts["RETAINED_RECOVERABLE"],
            "raw_unrecoverable": counts["RAW_UNRECOVERABLE"],
            "filter_loss_rate_of_raw_recoverable": counts["POST_OCR_FILTER_LOSS"] / (counts["POST_OCR_FILTER_LOSS"] + counts["RETAINED_RECOVERABLE"]) if counts["POST_OCR_FILTER_LOSS"] + counts["RETAINED_RECOVERABLE"] else 0.0,
        }

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped["overall"].append(row)
        grouped[f"document_type:{row['document_type']}"].append(row)
        grouped[f"field:{row['document_type']}:{row['field_base']}"].append(row)
    metrics = {
        "schema_version": "fintra-ocr-v2.post-ocr-filter-loss.v1",
        "contract": "Frozen Paddle OCR JSON versus the existing production region filter; Gold and OCR are read-only.",
        "documents": len({row["case_id"] for row in rows}),
        "overall": aggregate(grouped["overall"]),
        "by_document_type": {key.split(":", 1)[1]: aggregate(group) for key, group in sorted(grouped.items()) if key.startswith("document_type:")},
        "by_field": {key.split(":", 1)[1]: aggregate(group) for key, group in sorted(grouped.items()) if key.startswith("field:")},
        "gold_modified": False,
        "ocr_modified": False,
        "diagnostic_only": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["case_id", "document_id", "document_type", "field_name", "status"]
    with (output / "filter_loss_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output / "filter_loss_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Post-OCR filter loss",
        "",
        "This is a diagnostic comparison of raw frozen Paddle regions and the existing production fragment-filtered regions.",
        "Gold, OCR JSON, and source annotations were not modified.",
        "",
        "## Overall",
        "",
        f"```json\n{json.dumps(metrics['overall'], ensure_ascii=False, indent=2)}\n```",
        "",
        "## By document type",
        "",
    ]
    for kind, values in metrics["by_document_type"].items():
        report.append(f"- **{kind}**: {json.dumps(values, ensure_ascii=False)}")
    (output / "POST_OCR_FILTER_LOSS.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"documents": metrics["documents"], "overall": metrics["overall"], "output": str(output.resolve())}, ensure_ascii=False))
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--ocr-cases", type=Path, required=True)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--gt-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measure(args.cases, args.ocr_cases, args.gold_root, args.gt_root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

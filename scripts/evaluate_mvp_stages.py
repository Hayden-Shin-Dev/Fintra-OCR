"""Produce a reproducible OCR-vs-extractor development report.

This diagnostic consumes only frozen OCR JSON, frozen Gold, and an evaluator
CSV.  It never calls OCR, changes Gold, or uses a prediction to create Gold.
The Accurate75/Fast300 reports use MVP_DEVELOPMENT_GOLD_V4; an optional DEV60
report is explicitly labelled as its historical contract when supplied.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import evaluate_ocr_stages as stage


@dataclass(frozen=True)
class Dataset:
    name: str
    cases: Path
    ocr_cases: Path
    gold_root: Path | None
    gt_root: Path
    field_results: Path
    gold_contract: str


def _base(name: str) -> str:
    return re.sub(r"^items\[\d+\]\.", "", name)


def _field_cluster(field: str) -> str:
    base = _base(field)
    if field.startswith("items["):
        return "ITEM_TABLE"
    if base in {"seller", "buyer", "exporter", "consignee", "shipper", "notify_party"}:
        return "PARTY_BLOCK"
    if base in {"port_of_loading", "port_of_discharge"}:
        return "PORT"
    if base in {"invoice_number", "packing_list_number", "bl_number"}:
        return "IDENTIFIER"
    if base in {"currency", "total_amount", "quantity", "unit", "unit_price", "amount", "package_count", "gross_weight", "net_weight", "weight_unit"}:
        return "NUMERIC_MAPPING"
    return "OTHER"


def _ocr_cluster(row: dict[str, Any]) -> str:
    classification = row["classification"]
    if classification == "OCR_DETECTION_MISSING":
        return "detection"
    if classification == "OCR_MINOR_CHARACTER_ERROR":
        return "recognition"
    if row.get("candidate_count", 0) > 1:
        return "fragmentation_or_merge"
    if row.get("field_base", "").startswith("items["):
        return "table_layout"
    return "recognition"


def _correct(extracted: dict[str, str] | None) -> bool:
    return bool(extracted and extracted.get("status") in {"exact_match", "normalized_match"})


def _read_extracted(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}


def evaluate_dataset(dataset: Dataset) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    extracted = _read_extracted(dataset.field_results)
    rows: list[dict[str, Any]] = []
    for case_path in sorted(item for item in dataset.cases.iterdir() if item.is_dir()):
        manifest_path = case_path / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        case_id = str(manifest["case_id"])
        recognition_dir = dataset.ocr_cases / case_id / "outputs" / "recognition"
        ocr_path = recognition_dir / "paddle.json"
        if not ocr_path.is_file() and dataset.gold_contract == "DEV60_LEGACY_GOLD":
            candidates = sorted(recognition_dir.glob("*.json"))
            if len(candidates) == 1:
                ocr_path = candidates[0]
        gold_path = (dataset.gold_root / case_id / "semantic_gold_fields.json"
                     if dataset.gold_root else case_path / "semantic_gold_fields.json")
        gold_records = json.loads(gold_path.read_text(encoding="utf-8"))
        if dataset.gold_contract == "DEV60_LEGACY_GOLD":
            gold_records = manifest.get("gold_fields", gold_records)
        gt_case = dataset.gt_root / case_id
        gt_path = gt_case / "gt.json" if (gt_case / "gt.json").is_file() else gt_case / "source_annotation.json"
        if not ocr_path.is_file() or not gold_path.is_file() or not gt_path.is_file():
            raise FileNotFoundError(f"missing evaluation input for {case_id}: OCR={ocr_path}, Gold={gold_path}, GT={gt_path}")
        case = {"path": case_path, "case_id": case_id, "document_id": manifest["document_id"], "document_type": manifest["document_type"], "gt_path": gt_path}
        evidence_rows = stage._field_evidence(
            case,
            "paddle",
            stage._read_ocr(ocr_path),
            dataset.gold_root,
            gold_fields=gold_records,
        )
        for item in evidence_rows:
            prediction = extracted.get((case_id, item["field_name"]), {})
            raw_recoverable = item["classification"] in stage.RECOVERABLE
            final_correct = _correct(prediction)
            candidate_hit = raw_recoverable and stage._candidate_hit(prediction, item)
            resolver_correct = candidate_hit and final_correct
            if not raw_recoverable:
                failure_class = "OCR_FAILURE"
                subtype = _ocr_cluster(item)
            elif not final_correct:
                failure_class = "EXTRACTOR_FAILURE"
                subtype = _field_cluster(item["field_name"])
            else:
                failure_class = "NONE"
                subtype = "NONE"
            rows.append({
                "dataset": dataset.name,
                "gold_contract": dataset.gold_contract,
                "case_id": case_id,
                "document_id": manifest["document_id"],
                "document_type": manifest["document_type"],
                "field_name": item["field_name"],
                "field_base": item["field_base"],
                "gt_value": item["gt_value"],
                "ocr_classification": item["classification"],
                "raw_ocr_recoverable": raw_recoverable,
                "candidate_hit": candidate_hit,
                "resolver_correct": resolver_correct,
                "failure_class": failure_class,
                "failure_subtype": subtype,
                "candidate_count": item["candidate_count"],
                "closest_ocr_text": item["closest_ocr_text"],
                "combined_ocr_text": item["combined_ocr_text"],
                "neighboring_ocr_texts": item["neighboring_ocr_texts"],
                "predicted_value": prediction.get("predicted_value", ""),
                "extractor_status": prediction.get("status", "missing"),
                "extractor_source_text": prediction.get("source_text", ""),
                "extractor_correct": final_correct,
                "fuzzy_similarity": item["fuzzy_similarity"],
                "fuzzy_cer": item["fuzzy_cer"],
            })

    def aggregate(subset: list[dict[str, Any]]) -> dict[str, Any]:
        applicable = len(subset)
        recoverable = sum(row["raw_ocr_recoverable"] for row in subset)
        candidate_hit = sum(row["candidate_hit"] for row in subset)
        resolver_correct = sum(row["resolver_correct"] for row in subset)
        correct = sum(row["extractor_correct"] for row in subset)
        return {
            "applicable": applicable,
            "recoverable": recoverable,
            "candidate_hit": candidate_hit,
            "resolver_correct": resolver_correct,
            "final_correct": correct,
            "ocr_recoverability": recoverable / applicable if applicable else 0.0,
            "candidate_recall_on_recoverable": candidate_hit / recoverable if recoverable else 0.0,
            "resolver_accuracy_on_candidate_hit": resolver_correct / candidate_hit if candidate_hit else 0.0,
            "final_accuracy": correct / applicable if applicable else 0.0,
        }

    by_type = {kind: aggregate([row for row in rows if row["document_type"] == kind]) for kind in ("Commercial Invoice", "Packing List", "B/L")}
    by_field = {key: aggregate(group) for key, group in sorted(_groups(rows, ("document_type", "field_base")).items())}
    failure_counts = Counter((row["failure_class"], row["failure_subtype"]) for row in rows if row["failure_class"] != "NONE")
    metrics = {
        "schema_version": "fintra-ocr-v2.mvp-stage-evaluation.v1",
        "dataset": dataset.name,
        "gold_contract": dataset.gold_contract,
        "documents": len({row["case_id"] for row in rows}),
        "overall": aggregate(rows),
        "by_document_type": by_type,
        "by_field": by_field,
        "failure_counts": {f"{kind}:{subtype}": count for (kind, subtype), count in sorted(failure_counts.items())},
        "ocr_failure_by_type": _nested_counts(rows, "OCR_FAILURE"),
        "extractor_failure_by_type": _nested_counts(rows, "EXTRACTOR_FAILURE"),
        "prediction_blind_gold": True,
        "ocr_modified": False,
        "gold_modified": False,
    }
    return rows, metrics


def _groups(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[" / ".join(str(row[key]) for key in keys)].append(row)
    return result


def _nested_counts(rows: list[dict[str, Any]], failure_class: str) -> dict[str, Any]:
    by_type: dict[str, Counter] = defaultdict(Counter)
    by_field: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        if row["failure_class"] != failure_class:
            continue
        by_type[row["document_type"]][row["failure_subtype"]] += 1
        by_field[f"{row['document_type']}:{row['field_base']}"][row["failure_subtype"]] += 1
    return {"by_document_type": {key: dict(value) for key, value in sorted(by_type.items())}, "by_field": {key: dict(value) for key, value in sorted(by_field.items())}}


def write_report(
    datasets: list[Dataset],
    output: Path,
    *,
    final_holdout_2_accessed: bool = False,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    reports: dict[str, Any] = {}
    for dataset in datasets:
        rows, metrics = evaluate_dataset(dataset)
        all_rows.extend(rows)
        reports[dataset.name] = metrics
    csv_path = output / "field_stage_results.csv"
    fields = list(all_rows[0]) if all_rows else ["dataset"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(all_rows)
    payload = {"schema_version": "fintra-ocr-v2.mvp-stage-reports.v1", "datasets": reports, "output": str(output.resolve()), "final_holdout_2_accessed": final_holdout_2_accessed}
    (output / "mvp_stage_metrics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# MVP OCR vs extractor development stages", "", "The report uses frozen Paddle OCR JSON and prediction-blind Gold. It does not run OCR or alter Gold.", ""]
    for name, metrics in reports.items():
        overall = metrics["overall"]
        lines += [f"## {name}", "", f"Gold contract: `{metrics['gold_contract']}`", f"Documents: {metrics['documents']}", f"Overall: {overall['final_correct']}/{overall['applicable']} = {overall['final_accuracy']:.6f}", f"OCR recoverability: {overall['recoverable']}/{overall['applicable']} = {overall['ocr_recoverability']:.6f}", "", "| Scope | Applicable | Recoverable | Candidate hit | Final correct | OCR recoverability | Candidate recall | Resolver accuracy | Final accuracy |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for scope, item in [("Overall", overall), *metrics["by_document_type"].items()]:
            lines.append(f"| {scope} | {item['applicable']} | {item['recoverable']} | {item['candidate_hit']} | {item['final_correct']} | {item['ocr_recoverability']:.4f} | {item['candidate_recall_on_recoverable']:.4f} | {item['resolver_accuracy_on_candidate_hit']:.4f} | {item['final_accuracy']:.4f} |")
        lines += ["", "### Failure clusters", "", "```json", json.dumps({"ocr": metrics["ocr_failure_by_type"], "extractor": metrics["extractor_failure_by_type"]}, ensure_ascii=False, indent=2), "```", ""]
    (output / "MVP_STAGE_EVALUATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"datasets": list(reports), "output": str(output.resolve()), "final_holdout_2_accessed": final_holdout_2_accessed}, ensure_ascii=False))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accurate-cases", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1")
    parser.add_argument("--accurate-ocr-cases", type=Path, default=None)
    parser.add_argument("--accurate-gold-root", type=Path, default=ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-accurate75/cases")
    parser.add_argument("--accurate-gt-root", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/cases")
    parser.add_argument("--accurate-field-results", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/mvp-v4-iter2/accurate75-1/field_results.csv")
    parser.add_argument("--fast-cases", type=Path, default=ROOT / ".tmp/mvp_fast300_cases_v1")
    parser.add_argument("--fast-ocr-cases", type=Path, default=None)
    parser.add_argument("--fast-gold-root", type=Path, default=ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-balanced300/cases")
    parser.add_argument("--fast-gt-root", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/balanced300-eval-cases-v1")
    parser.add_argument("--fast-field-results", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/mvp-v4-iter2/fast300/field_results.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/mvp-v4-iter2/stages")
    parser.add_argument("--dev-cases", type=Path, default=None)
    parser.add_argument("--dev-ocr-cases", type=Path, default=None)
    parser.add_argument("--dev-field-results", type=Path, default=None)
    args = parser.parse_args()
    accurate_ocr = args.accurate_ocr_cases or args.accurate_cases
    fast_ocr = args.fast_ocr_cases or args.fast_cases
    datasets = [
        Dataset("Accurate75-1", args.accurate_cases, accurate_ocr, args.accurate_gold_root, args.accurate_gt_root, args.accurate_field_results, "MVP_DEVELOPMENT_GOLD_V4"),
        Dataset("Fast300", args.fast_cases, fast_ocr, args.fast_gold_root, args.fast_gt_root, args.fast_field_results, "MVP_DEVELOPMENT_GOLD_V4"),
    ]
    if args.dev_cases and args.dev_field_results:
        dev_ocr = args.dev_ocr_cases or args.dev_cases
        datasets.append(Dataset("DEV60-legacy", args.dev_cases, dev_ocr, None, args.dev_cases, args.dev_field_results, "DEV60_LEGACY_GOLD"))
    write_report(datasets, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

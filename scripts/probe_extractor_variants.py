"""Compare extractor variants on frozen OCR and Gold inputs.

This is a development probe only.  It never runs OCR, modifies Gold, or
changes the production call graph.  Each variant is evaluated against the
same case directory and evaluator normalization contract.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.extraction import documents
from scripts import evaluate_field_extraction as evaluator
from scripts import evaluate_ocr_stages as stages


VARIANTS = (
    "legacy",
    "typed",
    "ordered",
    "typed_ordered",
    "active",
    "layout",
    "table",
    "fragment_on_active",
    "fragment_off_active",
)


def _payload(result, variant: str) -> dict[str, Any]:
    if variant == "typed_ordered":
        from fintra.extraction.refinement import ordered_refinement, typed_refinement

        funcs = {
            "Commercial Invoice": documents.extract_commercial_invoice_legacy,
            "Packing List": documents.extract_packing_list_legacy,
            "B/L": documents.extract_bill_of_lading_legacy,
        }
        return ordered_refinement(result, typed_refinement(result, funcs[result.document_type](result))).to_dict()
    return evaluator._document_payload(result, "active" if variant == "fragment_on_active" else "active" if variant == "fragment_off_active" else variant)


@contextmanager
def _fragment_mode(variant: str) -> Iterator[None]:
    if variant != "fragment_off_active":
        yield
        return
    original = documents._regions

    def no_filter(result):
        return sorted(result.regions, key=lambda item: (item.page, item.bbox[1], item.bbox[0], item.index))

    documents._regions = no_filter
    try:
        yield
    finally:
        documents._regions = original


def _gold_path(case_dir: Path, gold_root: Path | None) -> Path:
    return (gold_root / case_dir.name / "semantic_gold_fields.json") if gold_root else case_dir / "semantic_gold_fields.json"


def _evaluate_dataset(name: str, cases_root: Path, gold_root: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output_rows: list[dict[str, Any]] = []
    cases = []
    for case_dir in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cases.append((case_dir, manifest))

    for case_dir, manifest in cases:
        result = evaluator._case_prediction(case_dir)
        gold = json.loads(_gold_path(case_dir, gold_root).read_text(encoding="utf-8"))
        evidence = stages._field_evidence(
            {"path": case_dir, "case_id": manifest["case_id"], "document_id": manifest["document_id"], "document_type": manifest["document_type"]},
            "paddle",
            stages._read_ocr(Path(next((case_dir / "outputs" / "recognition").glob("*.json")))),
            gold_root,
        )
        recoverable = {row["field_name"]: row["classification"] in stages.RECOVERABLE for row in evidence}
        for variant in VARIANTS:
            with _fragment_mode(variant):
                payload = _payload(result, variant)
            for field in gold:
                predicted = evaluator._predicted_field(payload, field["field_name"])
                prediction_status = str(predicted.get("status", "missing"))
                if field.get("status") != "available":
                    status = "not_applicable" if field.get("status") == "not_applicable" else "ambiguous"
                    correct = False
                elif prediction_status != "extracted" or predicted.get("value") in (None, ""):
                    status = "missing"
                    correct = False
                else:
                    status = evaluator.compare_field(predicted.get("value"), field.get("value"), field["field_name"])
                    correct = status in {"exact_match", "normalized_match"}
                output_rows.append({
                    "dataset": name,
                    "variant": variant,
                    "case_id": manifest["case_id"],
                    "document_type": manifest["document_type"],
                    "field_name": field["field_name"],
                    "gt_status": field.get("status"),
                    "status": status,
                    "correct": correct,
                    "raw_ocr_recoverable": recoverable.get(field["field_name"], False),
                    "predicted_value": predicted.get("value") if prediction_status == "extracted" else "",
                    "source_text": predicted.get("source_text", ""),
                    "confidence": predicted.get("confidence"),
                })

    summaries: dict[str, Any] = {}
    for variant in VARIANTS:
        subset = [row for row in output_rows if row["variant"] == variant]

        def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
            applicable = [row for row in rows if row["gt_status"] == "available"]
            correct = sum(row["correct"] for row in applicable)
            recoverable = sum(row["raw_ocr_recoverable"] for row in applicable)
            recoverable_correct = sum(row["raw_ocr_recoverable"] and row["correct"] for row in applicable)
            return {
                "applicable": len(applicable),
                "correct": correct,
                "accuracy": correct / len(applicable) if applicable else 0.0,
                "ocr_recoverable": recoverable,
                "correct_among_ocr_recoverable": recoverable_correct,
                "recovery_rate": recoverable_correct / recoverable if recoverable else 0.0,
                "wrong": sum(row["status"] == "wrong" for row in applicable),
                "missing": sum(row["status"] == "missing" for row in applicable),
            }

        summaries[variant] = {
            "overall": aggregate(subset),
            "by_document_type": {
                kind: aggregate([row for row in subset if row["document_type"] == kind])
                for kind in ("Commercial Invoice", "Packing List", "B/L")
            },
            "by_field": {
                f"{kind}:{field}": aggregate([row for row in subset if row["document_type"] == kind and row["field_name"] == field])
                for kind, field in sorted({(row["document_type"], row["field_name"]) for row in subset})
            },
        }
    return output_rows, {"dataset": name, "documents": len(cases), "variants": summaries}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accurate-cases", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1")
    parser.add_argument("--accurate-gold-root", type=Path, default=ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-accurate75/cases")
    parser.add_argument("--fast-cases", type=Path, default=ROOT / "artifacts/fintra/train-scale-v1/balanced300-eval-cases-v1")
    parser.add_argument("--fast-gold-root", type=Path, default=ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-balanced300/cases")
    parser.add_argument("--dev-cases", type=Path, default=ROOT / "artifacts/fintra/field_eval/cases")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/fintra/extractor-rebuild/probe")
    args = parser.parse_args()
    datasets = (
        ("Accurate75-1", args.accurate_cases, args.accurate_gold_root),
        ("Fast300", args.fast_cases, args.fast_gold_root),
        ("DEV60-legacy", args.dev_cases, None),
    )
    all_rows: list[dict[str, Any]] = []
    reports: dict[str, Any] = {}
    for name, cases, gold in datasets:
        rows, report = _evaluate_dataset(name, cases, gold)
        all_rows.extend(rows)
        reports[name] = report
    args.output.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / "variant_field_results.csv"
    fields = list(all_rows[0]) if all_rows else ["dataset"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)
    (args.output / "variant_probe_metrics.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Extractor variant probe", "", "All variants use frozen OCR and the selected Gold; no OCR or Gold mutation is performed.", ""]
    for dataset, report in reports.items():
        lines += [f"## {dataset}", "", "| Variant | Overall | OCR recoverable | Correct/recoverable | CI | PL | B/L |", "|---|---:|---:|---:|---:|---:|---:|"]
        for variant, metrics in report["variants"].items():
            overall = metrics["overall"]
            values = [metrics["by_document_type"][kind]["accuracy"] for kind in ("Commercial Invoice", "Packing List", "B/L")]
            lines.append(f"| {variant} | {overall['correct']}/{overall['applicable']} ({overall['accuracy']:.4f}) | {overall['ocr_recoverable']}/{overall['applicable']} | {overall['correct_among_ocr_recoverable']}/{overall['ocr_recoverable']} ({overall['recovery_rate']:.4f}) | {values[0]:.4f} | {values[1]:.4f} | {values[2]:.4f} |")
        lines.append("")
    (args.output / "EXTRACTOR_VARIANT_PROBE.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"datasets": list(reports), "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Compare isolated OCR v2 artifacts with frozen production OCR artifacts."""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fintra.ocr_v2.merge import _duplicate, _merge_pair
from fintra.ocr_v2.models import RawOCRRegion


DATASETS = ("accurate75", "fast300", "v3_75")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalized_regions(path: Path) -> list[RawOCRRegion]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    regions = []
    for index, region in enumerate(payload.get("regions", [])):
        regions.append(RawOCRRegion(index, str(region.get("text", "")), region.get("confidence"), region.get("polygon", [])))
    return regions


def pair_stats(regions: list[RawOCRRegion]) -> tuple[int, int]:
    duplicate_pairs = 0
    fragment_pairs = 0
    for left in range(len(regions)):
        for right in range(left + 1, len(regions)):
            duplicate_pairs += int(_duplicate(regions[left], regions[right]))
            fragment_pairs += int(_merge_pair(regions[left], regions[right]))
    return duplicate_pairs, fragment_pairs


def load_audit(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    return {(row["case_id"], row["document_type"], row["field"]): row for row in read_csv(path / "ocr_audit_field_recoverability.csv")}


def main() -> None:
    output = ROOT / "artifacts/fintra/ocr-v2"
    baseline_dirs = {
        "accurate75": ROOT / "artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1",
        "fast300": ROOT / ".tmp/mvp_fast300_cases_v1",
        "v3_75": ROOT / "artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3/cases",
    }
    v2_dirs = {name: output / name / "cases" for name in DATASETS}
    # Both backends are evaluated from the same frozen evaluator artifacts.
    # The production report contains all three datasets, while the v2 report
    # is generated as one combined readiness directory.
    v2_audit = output / "readiness"
    baseline_audit = ROOT / "artifacts/fintra/ocr-audit-readiness"
    baseline_rows = load_audit(baseline_audit)
    v2_rows = load_audit(v2_audit)
    comparison_rows: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []
    benchmark: dict[str, object] = {}
    for dataset in DATASETS:
        baseline = {key: row for key, row in baseline_rows.items() if key in baseline_rows and row.get("dataset", dataset) == dataset}
        v2 = {key: row for key, row in v2_rows.items() if key in v2_rows and row.get("dataset", dataset) == dataset}
        keys = sorted(set(baseline) | set(v2))
        grouped: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        for key in keys:
            before = baseline.get(key, {})
            after = v2.get(key, {})
            if not before or not after:
                continue
            field_key = (key[1], key[2])
            before_ok = before.get("status") in {"EXACT", "USABLE"}
            after_ok = after.get("status") in {"EXACT", "USABLE"}
            grouped[field_key]["applicable"] += 1
            grouped[field_key]["baseline_recoverable"] += int(before_ok)
            grouped[field_key]["v2_recoverable"] += int(after_ok)
            if not before_ok and after_ok:
                grouped[field_key]["gained"] += 1
            if before_ok and not after_ok:
                grouped[field_key]["lost"] += 1
            if before.get("status") != after.get("status"):
                failure_rows.append({"dataset": dataset, "case_id": key[0], "document_type": key[1], "field": key[2], "production_status": before.get("status"), "v2_status": after.get("status"), "production_text": before.get("ocr_best_text", ""), "v2_text": after.get("ocr_best_text", "")})
        for (document_type, field), counts in sorted(grouped.items()):
            applicable = counts["applicable"]
            comparison_rows.append({"dataset": dataset, "document_type": document_type, "field": field, "applicable": applicable, "production_recoverable": counts["baseline_recoverable"], "v2_recoverable": counts["v2_recoverable"], "gained": counts["gained"], "lost": counts["lost"], "production_rate": counts["baseline_recoverable"] / applicable if applicable else 0.0, "v2_rate": counts["v2_recoverable"] / applicable if applicable else 0.0})

        v2_summary = json.loads((v2_audit / "ocr_readiness_summary.json").read_text(encoding="utf-8")) if (v2_audit / "ocr_readiness_summary.json").is_file() else {}
        benchmark[dataset] = {"production_audit": "artifacts/fintra/ocr-audit-readiness", "v2_audit": str(v2_audit.relative_to(ROOT)), "v2_summary": v2_summary.get("by_dataset", {}).get(dataset, v2_summary.get("overall", {}))}

        for case_dir in sorted(path for path in v2_dirs[dataset].iterdir() if path.is_dir()) if v2_dirs[dataset].is_dir() else []:
            result_path = case_dir / "outputs/recognition/paddle.json"
            if not result_path.is_file():
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            metadata = result.get("metadata", {})
            production_path = baseline_dirs[dataset] / case_dir.name / "outputs/recognition/paddle.json"
            production_regions = None
            production_duplicate_pairs = None
            production_fragment_pairs = None
            if production_path.is_file():
                production_list = normalized_regions(production_path)
                production_regions = len(production_list)
                production_duplicate_pairs, production_fragment_pairs = pair_stats(production_list)
            v2_list = normalized_regions(result_path)
            v2_duplicate_pairs, v2_fragment_pairs = pair_stats(v2_list)
            duplicate_rows = {
                "dataset": dataset,
                "case_id": case_dir.name,
                "production_resolved_regions": production_regions,
                "production_duplicate_pairs": production_duplicate_pairs,
                "production_fragment_pairs": production_fragment_pairs,
                "v2_raw_regions": metadata.get("raw_region_count", len(result.get("raw_regions", []))),
                "v2_resolved_regions": metadata.get("resolved_region_count", len(result.get("regions", []))),
                "v2_duplicate_pairs_after": v2_duplicate_pairs,
                "v2_fragment_pairs_after": v2_fragment_pairs,
                "v2_duplicate_groups": metadata.get("duplicate_groups", 0),
                "v2_removed_duplicates": metadata.get("removed_duplicates", 0),
                "v2_merged_fragments": metadata.get("merged_fragments", 0),
                "v2_pass_count": metadata.get("ocr_pass_count", 0),
            }
            comparison_rows.append({"dataset": dataset, "document_type": "__region_stats__", **duplicate_rows})

    field_fields = ["dataset", "document_type", "field", "applicable", "production_recoverable", "v2_recoverable", "gained", "lost", "production_rate", "v2_rate"]
    region_fields = ["dataset", "document_type", "field", "applicable", "production_recoverable", "v2_recoverable", "gained", "lost", "production_rate", "v2_rate", "case_id", "production_resolved_regions", "production_duplicate_pairs", "production_fragment_pairs", "v2_raw_regions", "v2_resolved_regions", "v2_duplicate_pairs_after", "v2_fragment_pairs_after", "v2_duplicate_groups", "v2_removed_duplicates", "v2_merged_fragments", "v2_pass_count"]
    write_csv(output / "field_comparison.csv", [row for row in comparison_rows if row.get("document_type") != "__region_stats__"], field_fields)
    write_csv(output / "duplicate_analysis.csv", [{key: row.get(key, "") for key in region_fields} for row in comparison_rows if row.get("document_type") == "__region_stats__"], region_fields)
    write_csv(output / "failure_analysis.csv", failure_rows, ["dataset", "case_id", "document_type", "field", "production_status", "v2_status", "production_text", "v2_text"])

    pass_rows = []
    for dataset in DATASETS:
        for case_dir in sorted((v2_dirs[dataset] / "").glob("*/outputs/recognition/paddle.json")) if v2_dirs[dataset].is_dir() else []:
            result = json.loads(case_dir.read_text(encoding="utf-8"))
            metadata = result.get("metadata", {})
            for pass_name, count in metadata.get("pass_region_counts", {}).items():
                pass_rows.append({"dataset": dataset, "case_id": case_dir.parents[2].name, "pass_name": pass_name, "regions": count})
    write_csv(output / "pass_ablation.csv", pass_rows, ["dataset", "case_id", "pass_name", "regions"])
    (output / "benchmark_summary.json").write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")

    report = ["# OCR v2 Result", "", "This experiment keeps production OCR/cache untouched. v2 writes only under `artifacts/fintra/ocr-v2`. ", "", f"- datasets: {', '.join(DATASETS)}", "- field comparison: `field_comparison.csv`", "- failure transitions: `failure_analysis.csv`", "- duplicate/fragment metrics: `duplicate_analysis.csv`", "- pass contribution: `pass_ablation.csv`", ""]
    (output / "final_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"output": str(output), "field_rows": len([r for r in comparison_rows if r.get('document_type') != '__region_stats__']), "failure_rows": len(failure_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

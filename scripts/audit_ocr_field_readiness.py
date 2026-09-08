"""Audit frozen OCR evidence for Audit Field Schema v2 critical fields.

This is an OCR-only diagnostic. It reads existing recognition JSON and the
already-frozen per-case Gold metadata; it never runs OCR, calls an extractor,
changes Gold, or writes into any OCR cache.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_TYPES = ("Commercial Invoice", "Packing List", "B/L")
DATASETS = {
    "accurate75": ROOT / "artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1",
    "fast300": ROOT / ".tmp/mvp_fast300_cases_v1",
    "v3_75": ROOT / "artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3/cases",
}

CRITICAL_FIELDS = {
    "Commercial Invoice": [
        "invoice_number", "invoice_date", "seller", "buyer", "consignee", "bl_number",
        "lc_number", "lc_date", "purchase_order_number", "currency", "total_amount",
        "vessel", "voyage_number", "departure_date", "port_of_loading", "port_of_discharge",
        "final_destination", "payment_terms", "incoterm", "description", "hs_code", "quantity",
        "unit", "unit_price", "amount", "po_number",
    ],
    "Packing List": [
        "document_number", "document_date", "invoice_reference", "exporter", "shipper",
        "consignee", "buyer", "package_count", "package_type", "gross_weight", "net_weight",
        "weight_unit", "measurement", "vessel", "voyage_number", "port_of_loading",
        "port_of_discharge", "final_destination", "description", "quantity", "unit",
    ],
    "B/L": [
        "bl_number", "document_date", "shipper", "consignee", "notify_party", "vessel",
        "voyage_number", "port_of_loading", "port_of_discharge", "place_of_receipt",
        "place_of_delivery", "final_destination", "container_number", "seal_number",
        "package_count", "gross_weight", "measurement", "goods_description",
    ],
}


def norm(text: Any) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).upper()
    text = text.replace("&", " AND ")
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def compact(text: Any) -> str:
    return norm(text).replace(" ", "")


def polygon_box(region: dict[str, Any]) -> tuple[float, float, float, float]:
    points = region.get("polygon") or region.get("bbox") or []
    if points and isinstance(points[0], (int, float)):
        points = list(zip(points[::2], points[1::2]))
    if not points:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def expand(box: tuple[float, float, float, float], x_factor: float = 0.8, y_factor: float = 1.4) -> tuple[float, float, float, float]:
    width = max(20.0, box[2] - box[0])
    height = max(20.0, box[3] - box[1])
    return (box[0] - width * x_factor, box[1] - height * y_factor,
            box[2] + width * x_factor, box[3] + height * y_factor)


def read_schema() -> dict[str, dict[str, Any]]:
    payload = json.loads((ROOT / "artifacts/fintra/schema-v2/field_schema_v2.json").read_text(encoding="utf-8"))
    definitions: dict[str, dict[str, Any]] = {}
    for field in payload["fields"]:
        name = field["canonical_name"]
        definitions.setdefault(name, field)
    return definitions


def label_present(regions: list[dict[str, Any]], aliases: list[str], target_box: tuple[float, float, float, float] | None) -> tuple[bool, str]:
    candidates = []
    for region in regions:
        text = str(region.get("text", "")).strip()
        if not text:
            continue
        normalized = norm(text)
        for alias in sorted(aliases, key=len, reverse=True):
            alias_norm = norm(alias)
            if alias_norm and (normalized == alias_norm or re.search(rf"(?:^| ){re.escape(alias_norm)}(?:$| )", normalized)):
                distance = 0.0
                if target_box is not None:
                    cx, cy = center(polygon_box(region))
                    tx, ty = center(target_box)
                    distance = abs(cx - tx) + abs(cy - ty)
                candidates.append((distance, text))
                break
    if not candidates:
        return False, ""
    return True, min(candidates, key=lambda item: item[0])[1]


def candidate_regions(regions: list[dict[str, Any]], target_box: tuple[float, float, float, float] | None) -> list[dict[str, Any]]:
    usable = [region for region in regions if str(region.get("text", "")).strip()]
    if target_box is None:
        return usable
    local = [region for region in usable if intersects(polygon_box(region), expand(target_box))]
    return local or usable


def ordered_windows(regions: list[dict[str, Any]], max_window: int = 7) -> list[tuple[str, list[dict[str, Any]]]]:
    ordered = sorted(regions, key=lambda region: (center(polygon_box(region))[1], center(polygon_box(region))[0]))
    windows: list[tuple[str, list[dict[str, Any]]]] = []
    for start in range(len(ordered)):
        for size in range(1, min(max_window, len(ordered) - start) + 1):
            selected = ordered[start:start + size]
            text = " ".join(str(region.get("text", "")) for region in selected)
            windows.append((compact(text), selected))
    return windows


def best_value_match(expected: str, regions: list[dict[str, Any]], target_box: tuple[float, float, float, float] | None) -> dict[str, Any]:
    expected_compact = compact(expected)
    if not expected_compact:
        return {"exact": False, "usable": False, "similarity": 0.0, "text": "", "regions": []}
    local = candidate_regions(regions, target_box)
    windows = ordered_windows(local)
    best: tuple[float, str, list[dict[str, Any]]] = (0.0, "", [])
    exact = None
    for candidate, selected in windows:
        if not candidate:
            continue
        score = SequenceMatcher(None, expected_compact, candidate).ratio()
        if score > best[0]:
            best = (score, " ".join(str(region.get("text", "")) for region in selected), selected)
        if candidate == expected_compact:
            exact = (" ".join(str(region.get("text", "")) for region in selected), selected)
            break
    if exact is not None:
        return {"exact": True, "usable": True, "similarity": 1.0, "text": exact[0], "regions": exact[1]}
    # Short identifiers need a stricter threshold than long company/description values.
    threshold = 0.84 if len(expected_compact) >= 12 else 0.90
    return {"exact": False, "usable": best[0] >= threshold, "similarity": best[0], "text": best[1], "regions": best[2]}


def load_cases(dataset: str, root: Path) -> list[dict[str, Any]]:
    cases = []
    if not root.is_dir():
        return cases
    for case_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        gold_path = case_dir / "semantic_gold_fields.json"
        ocr_path = case_dir / "outputs/recognition/paddle.json"
        if not (manifest_path.is_file() and gold_path.is_file() and ocr_path.is_file()):
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cases.append({
            "dataset": dataset,
            "case_id": manifest["case_id"],
            "document_type": manifest["document_type"],
            "gold": json.loads(gold_path.read_text(encoding="utf-8")),
            "regions": json.loads(ocr_path.read_text(encoding="utf-8")).get("regions", []),
        })
    return cases


def classify(case: dict[str, Any], field: str, definition: dict[str, Any], gold_record: dict[str, Any]) -> dict[str, Any]:
    expected = str(gold_record.get("value") or "")
    target = gold_record.get("bbox")
    target_box = None
    if target:
        target_box = polygon_box({"polygon": target})
    regions = case["regions"]
    label_ok, label_text = label_present(regions, definition.get("aliases", []), target_box)
    match = best_value_match(expected, regions, target_box)
    if match["exact"]:
        status = "EXACT"
    elif match["usable"]:
        status = "USABLE"
    elif label_ok:
        status = "LABEL_ONLY"
    elif match["text"]:
        status = "VALUE_ONLY"
    else:
        status = "MISSING"
    nearby = candidate_regions(regions, target_box)
    nearby_text = " | ".join(str(region.get("text", "")) for region in nearby[:12])
    if status == "MISSING":
        if nearby:
            issue = "recognition_or_fragmentation_near_gold_region"
        else:
            issue = "detection_or_region_missing_near_gold_bbox"
    elif status == "LABEL_ONLY":
        issue = "label_detected_value_not_recoverable"
    elif status == "VALUE_ONLY":
        issue = "value_detected_label_not_recoverable"
    elif status == "USABLE":
        issue = "minor_ocr_error_or_spacing_fragmentation"
    else:
        issue = "none"
    return {
        "dataset": case["dataset"],
        "case_id": case["case_id"],
        "document_type": case["document_type"],
        "field": field,
        "gold_status": gold_record.get("status", ""),
        "applicable": 1,
        "expected": expected,
        "gold_source_text": gold_record.get("source_text") or "",
        "status": status,
        "label_text": label_text,
        "ocr_best_text": match["text"],
        "ocr_nearby_text": nearby_text,
        "similarity": f"{match['similarity']:.6f}",
        "likely_ocr_issue": issue,
        "gold_bbox": json.dumps(target, ensure_ascii=False),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    for row in rows:
        key = (row["dataset"], row["document_type"], row["field"])
        grouped[key]["applicable"] += 1
        grouped[key][row["status"].lower()] += 1
    output = {}
    for (dataset, document_type, field), counts in sorted(grouped.items()):
        applicable = counts["applicable"]
        recoverable = counts["exact"] + counts["usable"]
        output[f"{dataset}|{document_type}|{field}"] = {
            "dataset": dataset,
            "document_type": document_type,
            "field": field,
            "applicable": applicable,
            "exact": counts["exact"],
            "usable": counts["usable"],
            "label_only": counts["label_only"],
            "value_only": counts["value_only"],
            "missing": counts["missing"],
            "usable_recoverability": recoverable / applicable if applicable else 0.0,
        }
    return output


def summarize(rows: list[dict[str, Any]], grouped: dict[str, Any]) -> dict[str, Any]:
    totals = Counter(row["status"].lower() for row in rows)
    by_dataset: dict[str, Counter[str]] = defaultdict(Counter)
    by_type: dict[str, Counter[str]] = defaultdict(Counter)
    by_field: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for bucket, key in ((by_dataset, row["dataset"]), (by_type, row["document_type"]), (by_field, row["field"])):
            bucket[key]["applicable"] += 1
            bucket[key][row["status"].lower()] += 1

    def render(bucket: dict[str, Counter[str]]) -> dict[str, Any]:
        result = {}
        for key, counts in sorted(bucket.items()):
            applicable = counts["applicable"]
            result[key] = {
                "applicable": applicable,
                "exact": counts["exact"],
                "usable": counts["usable"],
                "label_only": counts["label_only"],
                "value_only": counts["value_only"],
                "missing": counts["missing"],
                "usable_recoverability": (counts["exact"] + counts["usable"]) / applicable if applicable else 0.0,
            }
        return result

    critical_total = totals["exact"] + totals["usable"]
    top_best = sorted(
        ((field, stats) for field, stats in render(by_field).items() if stats["applicable"]),
        key=lambda item: (-item[1]["usable_recoverability"], -item[1]["applicable"], item[0]),
    )[:10]
    top_missing = sorted(
        ((field, stats) for field, stats in render(by_field).items() if stats["missing"]),
        key=lambda item: (-item[1]["missing"], item[0]),
    )[:10]
    top_incomplete = sorted(
        ((field, stats) for field, stats in render(by_field).items()
         if stats["label_only"] + stats["value_only"] + stats["missing"]),
        key=lambda item: (-(item[1]["label_only"] + item[1]["value_only"] + item[1]["missing"]), item[0]),
    )[:10]
    overall = {"applicable": len(rows)}
    for key in ("exact", "usable", "label_only", "value_only", "missing"):
        overall[key] = totals.get(key, 0)
    overall["usable_recoverability"] = critical_total / len(rows) if rows else 0.0
    return {
        "scope": "Gold status=available critical audit fields only; ambiguous_gt is excluded, not counted as OCR missing",
        "matching_policy": {
            "exact": "NFKC + uppercase + punctuation/whitespace normalization, exact compact value equality across one or up to seven reading-order OCR regions",
            "usable": "best compact SequenceMatcher ratio >= 0.90 for short values (<12 chars), >= 0.84 for longer values",
            "label": "normalized alias token-boundary match in OCR regions",
            "value_scope": "Gold bbox-expanded neighborhood when available, otherwise all OCR regions; evidence is never passed to an extractor",
        },
        "rows": len(rows),
        "overall": overall,
        "by_dataset": render(by_dataset),
        "by_document_type": render(by_type),
        "by_field": render(by_field),
        "top_10_best_read_fields": [{"field": field, **stats} for field, stats in top_best],
        "top_10_missing_critical_fields": [{"field": field, **stats} for field, stats in top_missing],
        "top_10_incomplete_critical_fields": [{"field": field, **stats} for field, stats in top_incomplete],
        "grouped_rows": grouped,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/ocr-audit-readiness"))
    parser.add_argument("--accurate75", type=Path, default=DATASETS["accurate75"])
    parser.add_argument("--fast300", type=Path, default=DATASETS["fast300"])
    parser.add_argument("--v3", type=Path, default=DATASETS["v3_75"])
    args = parser.parse_args()
    out = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    definitions = read_schema()
    dataset_roots = {"accurate75": args.accurate75, "fast300": args.fast300, "v3_75": args.v3}
    rows: list[dict[str, Any]] = []
    loaded = {}
    gold_excluded: dict[str, Counter[str]] = defaultdict(Counter)
    for dataset, root_value in dataset_roots.items():
        root = root_value if root_value.is_absolute() else ROOT / root_value
        loaded[dataset] = load_cases(dataset, root)
        for case in loaded[dataset]:
            for field in CRITICAL_FIELDS[case["document_type"]]:
                record = next((item for item in case["gold"] if item.get("field_name") == field), None)
                if not record or record.get("status") != "available" or not record.get("value"):
                    gold_excluded[dataset]["unavailable_or_ambiguous"] += 1
                    continue
                if field not in definitions:
                    continue
                rows.append(classify(case, field, definitions[field], record))
    grouped = aggregate(rows)
    summary = summarize(rows, grouped)
    summary["datasets"] = {name: {"path": str(dataset_roots[name]), "documents": len(cases)} for name, cases in loaded.items()}
    summary["gold_excluded_from_ocr_denominator"] = {name: dict(counts) for name, counts in gold_excluded.items()}
    summary["critical_field_definitions"] = CRITICAL_FIELDS

    with (out / "ocr_audit_field_recoverability.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["dataset"])
        writer.writeheader()
        writer.writerows(rows)
    missing_rows = [row for row in rows if row["status"] == "MISSING"]
    with (out / "critical_ocr_failures.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["case_id", "dataset", "document_type", "field", "expected", "ocr_nearby_text", "status", "likely_ocr_issue", "similarity"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fields} for row in missing_rows)
    (out / "ocr_readiness_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    overall_rate = summary["overall"]["usable_recoverability"]
    verdict = "READY" if overall_rate >= 0.85 else "CAUTION" if overall_rate >= 0.70 else "BLOCKED"
    report = [
        "# OCR Audit Readiness",
        "",
        "This is an OCR-only evidence audit over frozen Paddle OCR JSON. It does not measure extractor accuracy and does not rerun OCR.",
        "",
        f"- Scope rows: {summary['rows']}",
        f"- Overall critical recoverability: {overall_rate:.2%}",
        f"- Verdict: **{verdict}**",
        "- `applicable` means the frozen Gold field is `available`; unavailable/ambiguous Gold fields are excluded rather than counted as OCR missing.",
        "",
        "## Dataset",
        "",
    ]
    for name, stats in summary["by_dataset"].items():
        report.append(f"- {name}: {stats['exact'] + stats['usable']}/{stats['applicable']} = {stats['usable_recoverability']:.2%}")
    report.extend(["", "## Document type", ""])
    for name, stats in summary["by_document_type"].items():
        report.append(f"- {name}: {stats['exact'] + stats['usable']}/{stats['applicable']} = {stats['usable_recoverability']:.2%}")
    report.extend(["", "## Status counts", "", "```text"])
    for key in ("exact", "usable", "label_only", "value_only", "missing"):
        report.append(f"{key.upper()}={summary['overall'].get(key, 0)}")
    report.extend(["```", "", "## Interpretation", "", "- EXACT/USABLE are OCR evidence recoverability states only.", "- LABEL_ONLY and VALUE_ONLY indicate partial evidence, not extractor failures.", "- MISSING cases are listed in `critical_ocr_failures.csv`.", "- If pure MISSING is zero, `top_10_incomplete_critical_fields` identifies fields with partial evidence."])
    (out / "OCR_AUDIT_READINESS.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"datasets": summary["datasets"], "overall": summary["overall"], "verdict": verdict, "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Measure the recoverability ceiling of the frozen OCR evidence.

This is a diagnostic only.  It never runs OCR, calls an extractor, changes
Gold, or writes to an OCR cache.  A field is ``recoverable`` when its reviewed
Gold value can be found in one OCR region or a short reading-order sequence
near the reviewed Gold bbox, allowing only normalization/minor OCR damage.

The result is an OCR evidence ceiling, not an extractor score.  It is kept
separate from the field evaluator because the matching intentionally uses the
Gold bbox to answer the counterfactual question: "could an extractor recover
this value from the frozen regions?".
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DOCUMENT_TYPES = ("Commercial Invoice", "Packing List", "B/L")
DATASETS = {
    "Accurate75": ROOT / "artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1",
    "Fast300": ROOT / "artifacts/fintra/train-scale-v1/balanced300-eval-cases-v1",
    "v3-75": ROOT / "artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3/cases",
}
GOLD_ROOTS = {
    "Accurate75": ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-accurate75/cases",
    "Fast300": ROOT / "artifacts/fintra/gold_audit/semantic-v4-image-balanced300/cases",
    "v3-75": None,
}

CRITICAL_FIELDS = {
    "Commercial Invoice": {
        "invoice_number", "invoice_date", "seller", "buyer", "consignee",
        "bl_number", "lc_number", "lc_date", "purchase_order_number", "currency",
        "total_amount", "vessel", "voyage_number", "departure_date",
        "port_of_loading", "port_of_discharge", "final_destination", "payment_terms",
        "incoterm", "description", "hs_code", "quantity", "unit", "unit_price",
        "amount", "po_number",
    },
    "Packing List": {
        "document_number", "document_date", "invoice_reference", "exporter", "shipper",
        "consignee", "buyer", "package_count", "package_type", "gross_weight",
        "net_weight", "weight_unit", "measurement", "vessel", "voyage_number",
        "port_of_loading", "port_of_discharge", "final_destination", "description",
        "quantity", "unit",
    },
    "B/L": {
        "bl_number", "document_date", "shipper", "consignee", "notify_party", "vessel",
        "voyage_number", "port_of_loading", "port_of_discharge", "place_of_receipt",
        "place_of_delivery", "final_destination", "container_number", "seal_number",
        "package_count", "gross_weight", "measurement", "goods_description",
    },
}


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).upper()
    text = text.replace("&", " AND ")
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def compact(value: Any) -> str:
    return norm(value).replace(" ", "")


def base_field(field_name: str) -> str:
    return re.sub(r"^items\[\d+\]\.", "", field_name)


def box(value: Any) -> tuple[float, float, float, float] | None:
    points = value
    if isinstance(value, dict):
        points = value.get("polygon") or value.get("bbox")
    if not points:
        return None
    if isinstance(points[0], (int, float)):
        points = list(zip(points[::2], points[1::2]))
    if not points:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def center(value: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((value[0] + value[2]) / 2.0, (value[1] + value[3]) / 2.0)


def intersects(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    return not (first[2] < second[0] or second[2] < first[0] or first[3] < second[1] or second[3] < first[1])


def expand(target: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    width = max(20.0, target[2] - target[0])
    height = max(20.0, target[3] - target[1])
    return (target[0] - width * 0.8, target[1] - height * 1.4,
            target[2] + width * 0.8, target[3] + height * 1.4)


def read_regions(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    regions = []
    for index, item in enumerate(payload.get("regions", [])):
        polygon = item.get("polygon", item.get("bbox"))
        region_box = box(polygon)
        text = str(item.get("text") or "").strip()
        if region_box is not None and text:
            regions.append({"index": index, "text": text, "box": region_box, "confidence": item.get("confidence")})
    return regions


def nearby(regions: list[dict[str, Any]], target: tuple[float, float, float, float] | None) -> list[dict[str, Any]]:
    if target is None:
        return list(regions)
    selected = [item for item in regions if intersects(item["box"], expand(target))]
    return selected or list(regions)


def reading_windows(regions: list[dict[str, Any]], maximum: int = 7) -> list[tuple[str, list[dict[str, Any]]]]:
    ordered = sorted(regions, key=lambda item: (center(item["box"])[1], center(item["box"])[0]))
    windows = []
    for start in range(len(ordered)):
        for size in range(1, min(maximum, len(ordered) - start) + 1):
            selected = ordered[start:start + size]
            text = " ".join(item["text"] for item in selected).strip()
            windows.append((compact(text), selected))
    return windows


def label_present(regions: list[dict[str, Any]], aliases: list[str], target: tuple[float, float, float, float] | None) -> bool:
    target_center = center(target) if target else None
    candidates = []
    for region in regions:
        normalized = norm(region["text"])
        if any(normalized == norm(alias) or re.search(rf"(?:^| ){re.escape(norm(alias))}(?:$| )", normalized) for alias in aliases):
            distance = 0.0
            if target_center is not None:
                rc = center(region["box"])
                distance = abs(rc[0] - target_center[0]) + abs(rc[1] - target_center[1])
            candidates.append((distance, region))
    return bool(candidates)


def best_match(expected: str, regions: list[dict[str, Any]]) -> dict[str, Any]:
    expected_value = compact(expected)
    best = (0.0, "", [])
    if not expected_value:
        return {"exact": False, "usable": False, "similarity": 0.0, "text": "", "regions": []}
    for candidate, selected in reading_windows(regions):
        if candidate == expected_value:
            return {"exact": True, "usable": True, "similarity": 1.0, "text": " ".join(x["text"] for x in selected), "regions": selected}
        score = SequenceMatcher(None, expected_value.casefold(), candidate.casefold()).ratio()
        if score > best[0]:
            best = score, " ".join(x["text"] for x in selected), selected
    threshold = 0.90 if len(expected_value) < 12 else 0.84
    return {"exact": False, "usable": best[0] >= threshold, "similarity": best[0], "text": best[1], "regions": best[2]}


def aliases_for(field: str) -> list[str]:
    from fintra.extraction.v2.specs import SPECS
    return list(SPECS.get(field).aliases) if field in SPECS else [field.replace("_", " ")]


def load_rows(dataset: str, cases_root: Path) -> list[dict[str, Any]]:
    gold_root = GOLD_ROOTS[dataset]
    rows = []
    for case_dir in sorted(item for item in cases_root.iterdir() if item.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        ocr_path = case_dir / "outputs/recognition/paddle.json"
        gold_path = (gold_root / case_dir.name / "semantic_gold_fields.json") if gold_root else case_dir / "semantic_gold_fields.json"
        if not (manifest_path.is_file() and ocr_path.is_file() and gold_path.is_file()):
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        document_type = manifest["document_type"]
        regions = read_regions(ocr_path)
        for record in json.loads(gold_path.read_text(encoding="utf-8")):
            if record.get("status") != "available" or not record.get("value"):
                continue
            field = base_field(record["field_name"])
            target = box(record.get("bbox"))
            local = nearby(regions, target)
            match = best_match(str(record["value"]), local)
            label = label_present(regions, aliases_for(field), target)
            status = "EXACT" if match["exact"] else "USABLE" if match["usable"] else "LABEL_ONLY" if label else "VALUE_ONLY" if match["text"] else "MISSING"
            rows.append({
                "dataset": dataset, "case_id": manifest["case_id"], "document_type": document_type,
                "field_name": record["field_name"], "field": field, "gold_value": record["value"],
                "status": status, "similarity": f"{match['similarity']:.6f}",
                "best_ocr_text": match["text"], "label_detected": int(label),
                "gold_bbox": json.dumps(record.get("bbox"), ensure_ascii=False),
                "ocr_region_indices": json.dumps([item["index"] for item in match["regions"]]),
            })
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def metric(subset: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(item["status"] for item in subset)
        applicable = len(subset)
        recoverable = counts["EXACT"] + counts["USABLE"]
        return {
            "applicable": applicable,
            "exact": counts["EXACT"], "usable": counts["USABLE"],
            "label_only": counts["LABEL_ONLY"], "value_only": counts["VALUE_ONLY"],
            "missing": counts["MISSING"], "recoverable": recoverable,
            "recoverability": recoverable / applicable if applicable else 0.0,
        }

    by_type = {kind: metric([row for row in rows if row["document_type"] == kind]) for kind in DOCUMENT_TYPES}
    by_dataset = {dataset: metric([row for row in rows if row["dataset"] == dataset]) for dataset in DATASETS}
    by_field = {}
    for key in sorted({(row["dataset"], row["document_type"], row["field"]) for row in rows}):
        by_field["|".join(key)] = metric([row for row in rows if (row["dataset"], row["document_type"], row["field"]) == key])
    critical = {dataset: metric([row for row in rows if row["dataset"] == dataset and row["field"] in CRITICAL_FIELDS[row["document_type"]]]) for dataset in DATASETS}
    return {"rows": len(rows), "by_dataset": by_dataset, "by_document_type": by_type, "critical_by_dataset": critical, "by_field": by_field}


def write_report(output: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "ocr_oracle_ceiling.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(rows[0]) if rows else ["dataset"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output / "ocr_oracle_ceiling.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# OCR Oracle Ceiling", "", "This is frozen OCR evidence recoverability, not extractor accuracy.", "", "## Dataset", "", "| Dataset | Applicable | Exact | Usable | Label only | Value only | Missing | Recoverability |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, item in summary["by_dataset"].items():
        lines.append(f"| {name} | {item['applicable']} | {item['exact']} | {item['usable']} | {item['label_only']} | {item['value_only']} | {item['missing']} | {item['recoverability']:.4f} |")
    lines += ["", "## Critical fields", "", "| Dataset | Applicable | Recoverable | Recoverability |", "|---|---:|---:|---:|"]
    for name, item in summary["critical_by_dataset"].items():
        lines.append(f"| {name} | {item['applicable']} | {item['recoverable']} | {item['recoverability']:.4f} |")
    lines += ["", "## Document type", "", "| Type | Applicable | Recoverable | Recoverability |", "|---|---:|---:|---:|"]
    for name, item in summary["by_document_type"].items():
        lines.append(f"| {name} | {item['applicable']} | {item['recoverable']} | {item['recoverability']:.4f} |")
    (output / "OCR_ORACLE_CEILING.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/extractor-v2/oracle-ceiling"))
    args = parser.parse_args()
    rows = []
    for dataset, root in DATASETS.items():
        rows.extend(load_rows(dataset, root))
    summary = summarize(rows)
    write_report(args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir, rows, summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

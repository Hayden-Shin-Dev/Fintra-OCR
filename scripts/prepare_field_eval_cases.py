"""Select 60 real AI-Hub Validation pairs and build evidence-based field gold.

AI-Hub supplies word-level text annotations rather than semantic field labels.
The gold builder therefore uses the inspected document-template regions and
marks fields that have multiple/no unambiguous source values as
``ambiguous_gt`` or ``not_applicable``. It never invents a value.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any


SUFFIX = re.compile(r"(?:INV|PL|BL)(\d{2})", re.IGNORECASE)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def _kind(path: Path) -> str:
    upper = path.name.upper()
    return "Commercial Invoice" if "INV" in upper else "Packing List" if "PL" in upper else "B/L"


def _tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            continue
        result.append({
            "index": index,
            "text": "" if item.get("data") is None else str(item["data"]),
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
            "polygon": [[xs[i], ys[i]] for i in range(len(xs))],
        })
    return result


def _zone(tokens: list[dict[str, Any]], x1: float, x2: float, y1: float, y2: float) -> list[dict[str, Any]]:
    return sorted((item for item in tokens if item["bbox"][0] >= x1 and item["bbox"][2] <= x2 and item["bbox"][1] >= y1 and item["bbox"][3] <= y2), key=lambda item: (item["bbox"][1], item["bbox"][0], item["index"]))


def _join(items: list[dict[str, Any]]) -> str:
    return " ".join(item["text"].strip() for item in items if item["text"].strip())


def _row_centers(items: list[dict[str, Any]], minimum: float = 45) -> list[float]:
    centers = []
    for item in sorted(items, key=lambda value: (value["bbox"][1], value["bbox"][0])):
        center = (item["bbox"][1] + item["bbox"][3]) / 2
        if not centers or center - centers[-1] > minimum:
            centers.append(center)
    return centers


def _near(items: list[dict[str, Any]], center: float, tolerance: float = 42) -> list[dict[str, Any]]:
    return [item for item in items if abs((item["bbox"][1] + item["bbox"][3]) / 2 - center) <= tolerance]


def _evidence(field_name: str, items: list[dict[str, Any]], *, value: str | None = None, status: str = "available") -> dict[str, Any]:
    if status == "available" and not items:
        status = "ambiguous_gt"
    text = value if value is not None else _join(items)
    if items:
        bbox = [[min(item["bbox"][0] for item in items), min(item["bbox"][1] for item in items)],
                [max(item["bbox"][2] for item in items), min(item["bbox"][1] for item in items)],
                [max(item["bbox"][2] for item in items), max(item["bbox"][3] for item in items)],
                [min(item["bbox"][0] for item in items), max(item["bbox"][3] for item in items)]]
        source_text = _join(items)
    else:
        bbox, source_text = None, None
    return {"field_name": field_name, "value": text if status == "available" else None, "status": status,
            "source_text": source_text, "bbox": bbox, "source_token_indices": [item["index"] for item in items]}


def _token(tokens: list[dict[str, Any]], pattern: str) -> list[dict[str, Any]]:
    return [item for item in tokens if re.fullmatch(pattern, item["text"].strip(), re.I)]


def _ci_gold(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        _evidence("invoice_number", _zone(tokens, 850, 1320, 250, 360)),
        _evidence("invoice_date", _zone(tokens, 850, 1450, 360, 455)),
        _evidence("seller", _zone(tokens, 100, 850, 280, 520)),
        _evidence("buyer", _zone(tokens, 100, 850, 540, 760)),
        _evidence("currency", _token(tokens, r"USD|EUR|GBP|JPY|CNY|KRW")),
        _evidence("total_amount", [item for item in tokens if item["bbox"][0] >= 1200 and 1450 <= item["bbox"][1] <= 1650 and re.search(r"\d", item["text"])]),
    ]
    item_tokens = [item for item in tokens if 1000 <= item["bbox"][1] <= 1400]
    centers = _row_centers([item for item in item_tokens if 820 <= item["bbox"][0] <= 950])
    for index, center in enumerate(centers):
        row = _near(item_tokens, center)
        fields.extend([
            _evidence(f"items[{index}].description", [item for item in row if item["bbox"][0] < 700]),
            _evidence(f"items[{index}].quantity", [item for item in row if 820 <= item["bbox"][0] <= 950 and re.fullmatch(r"\d+(?:[.,]\d+)?", item["text"].strip())]),
            _evidence(f"items[{index}].unit", [item for item in row if 950 <= item["bbox"][0] <= 1100]),
            _evidence(f"items[{index}].unit_price", [item for item in row if 1100 <= item["bbox"][0] <= 1260]),
            _evidence(f"items[{index}].amount", [item for item in row if 1260 <= item["bbox"][0] <= 1520]),
        ])
    return fields


def _packing_gold(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        _evidence("packing_list_number", [], status="not_applicable"),
        _evidence("date", _zone(tokens, 1150, 1500, 170, 280)),
        _evidence("exporter", _zone(tokens, 100, 800, 280, 450)),
        _evidence("consignee", _zone(tokens, 100, 750, 480, 700)),
    ]
    item_tokens = [item for item in tokens if 1000 <= item["bbox"][1] <= 1520]
    centers = _row_centers([item for item in item_tokens if 800 <= item["bbox"][0] <= 950])
    for index, center in enumerate(centers):
        row = _near(item_tokens, center)
        fields.extend([
            _evidence(f"items[{index}].description", [item for item in row if item["bbox"][0] < 730]),
            _evidence(f"items[{index}].quantity", [item for item in row if 800 <= item["bbox"][0] <= 950 and re.fullmatch(r"\d+(?:[.,]\d+)?", item["text"].strip())]),
            _evidence(f"items[{index}].unit", [item for item in row if 800 <= item["bbox"][0] <= 950 and not re.fullmatch(r"\d+(?:[.,]\d+)?", item["text"].strip())]),
        ])
    package = _zone(tokens, 350, 650, 1650, 1825)
    gross = [item for item in tokens if 400 <= item["bbox"][0] <= 700 and 1750 <= item["bbox"][1] <= 1870 and re.search(r"\d", item["text"])]
    fields.extend([
        _evidence("package_count", package),
        _evidence("gross_weight", gross),
        _evidence("net_weight", [], status="ambiguous_gt"),
    ])
    units = _token(tokens, r"KG|KGS|G|GRAM|GRAMS")
    if not units and gross:
        units = [gross[0]] if re.search(r"KG|G", gross[0]["text"], re.I) else []
    fields.append(_evidence("weight_unit", units, value="KG" if units else None, status="available" if units else "ambiguous_gt"))
    return fields


def _bl_gold(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    goods = [item for item in tokens if 500 <= item["bbox"][0] <= 1100 and 1080 <= item["bbox"][1] <= 1500]
    gross = [item for item in tokens if 1100 <= item["bbox"][0] <= 1300 and 1080 <= item["bbox"][1] <= 1500 and re.search(r"\d", item["text"])]
    units = [item for item in gross if re.search(r"KG", item["text"], re.I)]
    return [
        _evidence("bl_number", _zone(tokens, 1150, 1500, 200, 300)),
        _evidence("shipper", [], status="not_applicable"),
        _evidence("consignee", [], status="ambiguous_gt"),
        _evidence("notify_party", _zone(tokens, 70, 800, 600, 800)),
        _evidence("vessel", _zone(tokens, 70, 400, 850, 980)),
        _evidence("port_of_loading", _zone(tokens, 400, 800, 850, 980)),
        _evidence("port_of_discharge", _zone(tokens, 70, 400, 950, 1080)),
        _evidence("shipment_date", [], status="not_applicable"),
        _evidence("package_count", [], status="ambiguous_gt"),
        _evidence("gross_weight", [], status="ambiguous_gt"),
        _evidence("weight_unit", units, value="KG" if units else None, status="available" if units else "ambiguous_gt"),
        _evidence("goods_description", goods),
    ]


def _gold(payload: dict[str, Any], document_type: str) -> list[dict[str, Any]]:
    tokens = _tokens(payload)
    if document_type == "Commercial Invoice":
        return _ci_gold(tokens)
    if document_type == "Packing List":
        return _packing_gold(tokens)
    return _bl_gold(tokens)


def _records(source_zip: Path, label_zip: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(source_zip) as source, zipfile.ZipFile(label_zip) as labels:
        images = {Path(name).name: name for name in source.namelist() if Path(name).suffix.lower() in IMAGE_EXTENSIONS}
        records = []
        for label_entry in labels.namelist():
            if not label_entry.lower().endswith(".json"):
                continue
            try:
                payload = json.loads(labels.read(label_entry).decode("utf-8"))
                image = payload["Images"]
                image_name = f"{image['identifier']}.{image['type']}"
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
                continue
            if image_name in images:
                records.append({"image_name": image_name, "source_entry": images[image_name], "label_entry": label_entry, "payload": payload})
        return sorted(records, key=lambda item: item["image_name"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--per-zip", type=int, default=4)
    args = parser.parse_args()
    source = {SUFFIX.search(path.name).group(0).upper(): path for path in (args.zip_root / "source").rglob("*.zip") if SUFFIX.search(path.name)}
    labels = {SUFFIX.search(path.name).group(0).upper(): path for path in (args.zip_root / "labels").rglob("*.zip") if SUFFIX.search(path.name)}
    grouped = {"Commercial Invoice": [], "Packing List": [], "B/L": []}
    for key in sorted(set(source) & set(labels)):
        kind = _kind(source[key])
        grouped[kind].extend((source[key], labels[key], item) for item in _records(source[key], labels[key])[:args.per_zip])
    if any(len(items) != 20 for items in grouped.values()):
        raise RuntimeError("expected exactly 20 selected records per document type")

    selected = []
    counters = {kind: 0 for kind in grouped}
    short = {"Commercial Invoice": "ci", "Packing List": "pl", "B/L": "bl"}
    for kind in ("Commercial Invoice", "Packing List", "B/L"):
        for source_zip, label_zip, item in grouped[kind]:
            counters[kind] += 1
            case_id = f"{short[kind]}-{counters[kind]:03d}"
            case_dir = args.output_root / "cases" / case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            image_path = case_dir / item["image_name"]
            gt_path = case_dir / "gt.json"
            with zipfile.ZipFile(source_zip) as source_file:
                image_path.write_bytes(source_file.read(item["source_entry"]))
            gt_path.write_text(json.dumps(item["payload"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            manifest = {
                "case_id": case_id, "document_id": str(item["payload"]["Images"]["identifier"]),
                "document_type": kind, "image": item["image_name"],
                "source_zip": str(source_zip), "label_zip": str(label_zip),
                "source_entry": item["source_entry"], "label_entry": item["label_entry"],
                "gt_annotations": len(item["payload"].get("bbox", [])),
                "gold_method": "AI-Hub word-level annotation plus inspected template zones",
                "gold_fields": _gold(item["payload"], kind),
            }
            (case_dir / "case_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            selected.append(manifest)
    result = {"schema_version": "fintra-ocr-v2.field-eval-selection.v1", "documents": selected, "counts": {kind: len(items) for kind, items in grouped.items()}}
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "selection_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False))
    print(f"OUTPUT_ROOT={args.output_root}")


if __name__ == "__main__":
    main()

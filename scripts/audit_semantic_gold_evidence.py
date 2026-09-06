"""Prediction-blind semantic Gold audit using original Training TL and images.

The AI-Hub label is word-level, not field-level.  This audit therefore never
infers semantics from OCR or extractor output.  It uses the original TL JSON,
the source token geometry, visible label/section anchors, typed values, and
the case image as provenance evidence.  Anything not decisively supported is
left conservative (SOURCE_AMBIGUOUS or CANNOT_VERIFY).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CANONICAL_WIDTH = 1654.0
CANONICAL_HEIGHT = 2340.0
LINE_TOLERANCE = 22.0

FIELD_ALIASES = {
    "invoice_number": ("invoice no", "invoice number", "invoice #"),
    "invoice_date": ("invoice date", "date of invoice", "invoice no and date"),
    "seller": ("shipper seller", "shipper/seller", "seller", "shipper"),
    "buyer": ("buyer", "consignee"),
    "currency": ("currency",),
    "total_amount": ("grand total", "total amount", "invoice total", "total"),
    "packing_list_number": ("packing list no", "packing list number", "packing list"),
    "date": ("date",),
    "exporter": ("exporter", "shipper", "shipper/exporter"),
    "consignee": ("consignee", "buyer"),
    "package_count": ("packages", "package", "no of packages", "number of packages", "pkgs"),
    "gross_weight": ("gross weight",),
    "net_weight": ("net weight",),
    "weight_unit": ("weight",),
    "bl_number": ("b/l no", "bl no", "bill of lading no", "b/l number"),
    "shipper": ("consignor shipper", "consignor/shipper", "shipper"),
    "notify_party": ("notify party", "notify"),
    "vessel": ("vessel/voy", "vessel / voy", "vessel", "export carrier"),
    "port_of_loading": ("port of loading",),
    "port_of_discharge": ("port of discharge",),
    "shipment_date": ("laden on board", "on board", "shipment date", "date of departure"),
    "goods_description": ("description of goods", "description of good", "goods description"),
}

PARTY_FIELDS = {"seller", "buyer", "exporter", "consignee", "shipper", "notify_party"}
PORT_FIELDS = {"port_of_loading", "port_of_discharge"}
ITEM_FIELDS = {"description", "quantity", "unit", "unit_price", "amount"}
TRANSPORT_TERMS = {"FOB", "CIF", "CFR", "DAF", "DDP", "DDU", "DEQ", "CFS", "CY"}
UNIT_WORDS = {"KG", "KGS", "G", "GRAM", "GRAMS", "PC", "PCS", "EA", "EACH", "PKG", "BOX", "CTN", "SET", "UNIT", "POUND", "YARD", "DRUM", "BAG", "PIECE", "ST"}
COUNTRIES = {"ARGENTINA", "AUSTRALIA", "BELGIUM", "BRAZIL", "CANADA", "CHILE", "CHINA", "DENMARK", "EGYPT", "FINLAND", "FRANCE", "GERMANY", "GREECE", "HAITI", "INDIA", "IRELAND", "ISRAEL", "ITALY", "JAPAN", "KOREA", "MALAYSIA", "MEXICO", "NIGERIA", "NORWAY", "POLAND", "SOUTH AFRICA", "SPAIN", "TAIWAN", "THAILAND", "TURKEY", "UNITED KINGDOM", "UNITED STATES", "VIETNAM", "VIET NAM"}


def norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()


def raw_tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            continue
        result.append({"index": index, "text": str(item.get("data") or "").strip(), "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return result


def page_size(payload: dict[str, Any]) -> tuple[float, float]:
    image = payload.get("Images", {})
    width, height = image.get("width"), image.get("height")
    if isinstance(width, (int, float)) and isinstance(height, (int, float)) and width > 0 and height > 0:
        return float(width), float(height)
    tokens = raw_tokens(payload)
    return max((x["bbox"][2] for x in tokens), default=CANONICAL_WIDTH), max((x["bbox"][3] for x in tokens), default=CANONICAL_HEIGHT)


def lines(tokens: list[dict[str, Any]], height: float) -> list[list[dict[str, Any]]]:
    tolerance = LINE_TOLERANCE / CANONICAL_HEIGHT * height
    groups: list[dict[str, Any]] = []
    for token in sorted(tokens, key=lambda x: ((x["bbox"][1] + x["bbox"][3]) / 2, x["bbox"][0], x["index"])):
        cy = (token["bbox"][1] + token["bbox"][3]) / 2
        group = next((g for g in groups if abs(g["cy"] - cy) <= tolerance), None)
        if group is None:
            group = {"cy": cy, "tokens": []}
            groups.append(group)
        group["tokens"].append(token)
        group["cy"] = sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in group["tokens"]) / len(group["tokens"])
    return [sorted(group["tokens"], key=lambda x: (x["bbox"][0], x["index"])) for group in sorted(groups, key=lambda x: x["cy"])]


def line_text(line: list[dict[str, Any]]) -> str:
    return " ".join(x["text"] for x in line).strip()


def field_leaf(name: str) -> str:
    return name.rsplit(".", 1)[-1]


def aliases_for(name: str) -> tuple[str, ...]:
    leaf = field_leaf(name)
    if leaf in FIELD_ALIASES:
        return FIELD_ALIASES[leaf]
    if leaf == "description":
        return ("description", "description of goods", "goods")
    return ()


def find_anchors(field_name: str, doc_type: str, grouped: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    aliases = [norm(x) for x in aliases_for(field_name)]
    found = []
    for line_no, line in enumerate(grouped):
        text = norm(line_text(line))
        if not text:
            continue
        # Word-level TL can contain boilerplate phrases that mention a party
        # role but are not that role's visible heading (for example
        # ``SHIPPER'S LOAD...`` or ``SAME AS CONSIGNEE AT ...``).
        if field_leaf(field_name) in PARTY_FIELDS and (
            "SHIPPER S LOAD" in text or "STOWAGE AND COUNT" in text or
            ("SAME AS CONSIGNEE" in text and field_leaf(field_name) != "notify_party") or
            (text.startswith("THE ") and field_leaf(field_name).upper() in text)
        ):
            continue
        if any(alias and (alias in text or all(word in text.split() for word in alias.split())) for alias in aliases):
            found.append({"line_no": line_no, "text": line_text(line), "tokens": line, "position": [min(x["bbox"][0] for x in line), min(x["bbox"][1] for x in line), max(x["bbox"][2] for x in line), max(x["bbox"][3] for x in line)]})
    return found


def field_box(field: dict[str, Any]) -> list[float] | None:
    value = field.get("bbox")
    if not isinstance(value, list) or not value:
        return None
    points = value if isinstance(value[0], list) else [[value[0], value[1]], [value[2], value[3]]]
    return [min(float(p[0]) for p in points), min(float(p[1]) for p in points), max(float(p[0]) for p in points), max(float(p[1]) for p in points)]


def selected_tokens(field: dict[str, Any], tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = {int(x) for x in field.get("source_token_indices", [])}
    return [x for x in tokens if x["index"] in wanted]


def type_issue(name: str, value: str) -> str | None:
    leaf = field_leaf(name)
    if leaf.endswith("description") or leaf == "goods_description":
        if not re.search(r"[A-Za-z]", value) or re.fullmatch(r"[\s$,+.\-/()0-9]+", value):
            return "description_is_not_textual"
    if leaf.endswith("quantity") or leaf.endswith("unit_price") or leaf.endswith("amount") or leaf in {"total_amount", "gross_weight", "net_weight", "package_count"}:
        if not re.search(r"\d", value):
            return "numeric_field_has_no_numeric_evidence"
    if leaf.endswith("unit") and not re.fullmatch(r"[A-Za-z]+", value.strip()):
        return "unit_is_not_alphabetic"
    if leaf in PORT_FIELDS and "," not in value:
        return "port_has_no_place_country_shape"
    if leaf == "vessel" and norm(value) in TRANSPORT_TERMS:
        return "vessel_is_transport_term"
    return None


def png_info(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    width = int.from_bytes(data[16:20], "big") if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24 else None
    height = int.from_bytes(data[20:24], "big") if width is not None else None
    return {"path": str(path), "exists": path.is_file(), "sha256": hashlib.sha256(data).hexdigest() if path.is_file() else None, "width": width, "height": height}


def semantic_verdict(field: dict[str, Any], doc_type: str, tokens: list[dict[str, Any]], grouped: list[list[dict[str, Any]]], width: float, height: float) -> tuple[str, str, list[dict[str, Any]]]:
    name = str(field["field_name"])
    value = str(field.get("value") or "").strip()
    if field.get("status") == "not_applicable":
        return "NOT_APPLICABLE", "Gold explicitly marks field not applicable", []
    if field.get("status") != "available" or not value:
        return "CANNOT_VERIFY", "Gold has no available source value", []
    selected = selected_tokens(field, tokens)
    if not selected:
        return "VERIFIED_ERROR", "available Gold has no source token evidence", []
    issue = type_issue(name, value)
    if issue:
        return "VERIFIED_ERROR", issue, []
    anchors = find_anchors(name, doc_type, grouped)
    leaf = field_leaf(name)
    box = field_box(field)
    if box is None:
        return "VERIFIED_ERROR", "available Gold has no geometry", anchors
    center_x, center_y = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    if not anchors:
        return "CANNOT_VERIFY", "no decisive semantic anchor in original TL", []
    if len(anchors) > 1:
        nearby = [a for a in anchors if abs(((a["position"][1] + a["position"][3]) / 2) - center_y) < .25 * height]
        if len(nearby) > 1:
            return "SOURCE_AMBIGUOUS", "multiple competing semantic anchors", anchors
    anchor = min(anchors, key=lambda a: abs(((a["position"][1] + a["position"][3]) / 2) - center_y))
    ax0, ay0, ax1, ay1 = anchor["position"]
    anchor_y = (ay0 + ay1) / 2
    same_column = center_x >= ax0 - .18 * width and center_x <= ax1 + .36 * width
    below_or_inline = center_y >= anchor_y - .02 * height and center_y <= anchor_y + .25 * height
    if leaf in PARTY_FIELDS or leaf in PORT_FIELDS or leaf in {"vessel", "shipment_date", "invoice_number", "invoice_date", "date", "bl_number"}:
        if not same_column or not below_or_inline:
            return "VERIFIED_ERROR", "Gold evidence lies outside anchor-relative field block", anchors
    if leaf in ITEM_FIELDS or leaf in {"goods_description", "total_amount", "currency", "gross_weight", "net_weight", "package_count", "weight_unit"}:
        # Table fields may be below their header by several lines.  Require a
        # plausible same-page table relation and a compatible type; do not
        # claim proof when the anchor is merely a generic word such as TOTAL.
        if leaf in {"total_amount", "currency"} and norm(anchor["text"]) in {"TOTAL", "AMOUNT"}:
            return "SOURCE_AMBIGUOUS", "generic total/amount anchor has competing semantic uses", anchors
        if center_y < anchor_y - .03 * height:
            return "VERIFIED_ERROR", "table evidence precedes its header anchor", anchors
    return "VERIFIED_CORRECT", "source token type and anchor-relative layout are consistent", anchors


def independent_rows(tokens: list[dict[str, Any]], width: float, height: float) -> list[float]:
    """Find likely table rows without reading Gold or predictions."""
    grouped = lines([x for x in tokens if .25 * height <= x["bbox"][1] <= .78 * height], height)
    candidates = []
    for line in grouped:
        text = norm(line_text(line))
        numeric = any(re.search(r"\d", x["text"]) for x in line if x["bbox"][0] >= .45 * width)
        textual = any(re.search(r"[A-Za-z]", x["text"]) for x in line if x["bbox"][0] <= .60 * width)
        if numeric and textual and not any(word in text.split() for word in ("TOTAL", "SUBTOTAL", "DESCRIPTION", "QUANTITY", "AMOUNT", "WEIGHT")):
            candidates.append(sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in line) / len(line))
    merged = []
    for value in candidates:
        if not merged or value - merged[-1] > .035 * height:
            merged.append(value)
    return merged


def find_original_tl(training_root: Path, identifier: str, index: dict[str, Path]) -> Path | None:
    label_root = next((p for p in training_root.iterdir() if p.is_dir() and p.name.startswith("02.")), training_root / "02.라벨링데이터")
    direct = label_root / f"{identifier}.json"
    if direct.is_file():
        return direct
    if identifier in index:
        return index[identifier]
    # The local case ID preserves the document-family prefix (BL/PL/NV),
    # while AI-Hub's TL Images.identifier may use a different family prefix.
    # The numeric sample suffix is the stable join key in that source export.
    suffix = identifier.rsplit("_", 1)[-1]
    matches = [path for key, path in index.items() if key.rsplit("_", 1)[-1] == suffix]
    return matches[0] if len(matches) == 1 else None


def load_original_tl(training_root: Path, manifest_row: dict[str, Any], source_payload: dict[str, Any], index: dict[str, Path]) -> tuple[dict[str, Any], str]:
    """Read the original TL entry from the Training TL archive when present."""
    label_root = next((p for p in training_root.iterdir() if p.is_dir() and p.name.startswith("02.")), training_root / "02.라벨링데이터")
    group = str(manifest_row.get("source_group", ""))
    archives = sorted(label_root.glob(f"TL*{group}.zip"))
    entry = str(manifest_row.get("label_entry", ""))
    if len(archives) == 1 and entry:
        candidates = [entry, entry.lstrip("/")]
        with zipfile.ZipFile(archives[0]) as handle:
            name = next((candidate for candidate in candidates if candidate in handle.namelist()), None)
            if name is not None:
                return json.loads(handle.read(name).decode("utf-8-sig")), f"{archives[0]}::{name}"
    identifier = str(source_payload.get("Images", {}).get("identifier", ""))
    path = find_original_tl(training_root, identifier, index)
    if path is None:
        raise FileNotFoundError(f"original Training TL not found for {manifest_row.get('stable_sample_id')}: {identifier}")
    return json.loads(path.read_text(encoding="utf-8-sig")), str(path)


def build_index(training_root: Path) -> dict[str, Path]:
    result = {}
    label_root = next((p for p in training_root.iterdir() if p.is_dir() and p.name.startswith("02.")), training_root / "02.라벨링데이터")
    for path in label_root.glob("*.json"):
        try:
            identifier = json.loads(path.read_text(encoding="utf-8-sig"))["Images"]["identifier"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        result[str(identifier)] = path
    return result


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    return {str(item["stable_sample_id"]): item for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip() for item in [json.loads(line)]}


def audit(allowlist: Path, manifest_path: Path, cases_root: Path, gold_root: Path, training_root: Path, old_root: Path, output_root: Path) -> dict[str, Any]:
    ids = [x.strip() for x in allowlist.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    manifest = load_manifest(manifest_path)
    tl_index = build_index(training_root)
    output_root.mkdir(parents=True, exist_ok=True)
    records, case_rows = [], []
    for case_id in ids:
        case = cases_root / case_id
        gold_case = gold_root / case_id
        case_manifest = json.loads((case / "case_manifest.json").read_text(encoding="utf-8"))
        source_payload = json.loads((case / "source_annotation.json").read_text(encoding="utf-8-sig"))
        identifier = str(source_payload.get("Images", {}).get("identifier", ""))
        original_payload, original_path = load_original_tl(training_root, manifest[case_id], source_payload, tl_index)
        tokens = raw_tokens(original_payload)
        width, height = page_size(original_payload)
        grouped = lines(tokens, height)
        image_meta = png_info(case / "image.png")
        fields = json.loads((gold_case / "semantic_gold_fields.json").read_text(encoding="utf-8"))
        for field in fields:
            verdict, reason, anchors = semantic_verdict(field, case_manifest["document_type"], tokens, grouped, width, height)
            selected = selected_tokens(field, tokens)
            old_field = {}
            old_path = old_root / case_id / "semantic_gold_fields.json"
            if old_path.is_file():
                old_field = {x["field_name"]: x for x in json.loads(old_path.read_text(encoding="utf-8"))}.get(field["field_name"], {})
            old_status = str(old_field.get("status") or "missing_or_nonexistent")
            new_status = str(field.get("status") or "missing_or_nonexistent")
            records.append({
                "case_id": case_id, "document_type": case_manifest["document_type"], "source_group": case_manifest.get("source_group", ""),
                "field_name": field["field_name"], "gold_status": new_status, "current_gold": field.get("value"),
                "semantic_status": verdict, "semantic_reason": reason, "anchor_text": " || ".join(a["text"] for a in anchors),
                "anchor_position": json.dumps([a["position"] for a in anchors], ensure_ascii=False),
                "gold_position": json.dumps(field_box(field), ensure_ascii=False), "source_token_indices": json.dumps(field.get("source_token_indices", [])),
                "source_text": " ".join(x["text"] for x in selected), "original_tl_path": str(original_path),
                "source_annotation_path": str(case / "source_annotation.json"), "image_path": image_meta["path"],
                "image_sha256": image_meta["sha256"], "image_width": image_meta["width"], "image_height": image_meta["height"],
                "old_status": old_status, "new_status": new_status, "denominator_transition": f"{old_status}_to_{new_status}",
                "prediction_blind": True, "ocr_read": False, "extractor_read": False, "final_holdout_2_accessed": False,
            })
        generated_rows = independent_rows(tokens, width, height) if case_manifest["document_type"] in {"Commercial Invoice", "Packing List"} else []
        gold_rows = sorted({int(m.group(1)) for field in fields for m in [re.match(r"items\[(\d+)\]", str(field["field_name"]))] if m})
        case_rows.append({"case_id": case_id, "document_type": case_manifest["document_type"], "source_group": case_manifest.get("source_group", ""), "independent_row_count": len(generated_rows), "gold_row_count": len(gold_rows), "row_count_delta": len(gold_rows) - len(generated_rows), "row_completeness_status": "PASS" if len(gold_rows) == len(generated_rows) else "CANNOT_VERIFY", "original_tl_path": str(original_path), "image_path": image_meta["path"], "image_exists": image_meta["exists"], "image_sha256": image_meta["sha256"], "original_identifier": identifier})
    field_path = output_root / "semantic_evidence_audit.csv"
    with field_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]) if records else ["case_id"]); writer.writeheader(); writer.writerows(records)
    rows_path = output_root / "semantic_row_completeness.csv"
    with rows_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(case_rows[0]) if case_rows else ["case_id"]); writer.writeheader(); writer.writerows(case_rows)
    statuses = Counter(x["semantic_status"] for x in records if x["gold_status"] == "available")
    by_type = defaultdict(Counter); by_field = defaultdict(Counter); by_group = defaultdict(Counter)
    for row in records:
        if row["gold_status"] != "available":
            continue
        by_type[row["document_type"]][row["semantic_status"]] += 1
        by_field[f"{row['document_type']}:{row['field_name']}"][row["semantic_status"]] += 1
        by_group[row["source_group"]][row["semantic_status"]] += 1
    summary = {
        "cases": len(ids), "available_fields": sum(x["gold_status"] == "available" for x in records), "semantic_classification": dict(statuses),
        "semantic_by_document_type": {k: dict(v) for k, v in by_type.items()}, "semantic_by_field": {k: dict(v) for k, v in by_field.items()}, "semantic_by_source_group": {k: dict(v) for k, v in by_group.items()},
        "source_tl_files_resolved": len({x["original_tl_path"] for x in records}), "images_present": sum(x["image_exists"] for x in case_rows), "row_cases": len(case_rows),
        "row_pass": sum(x["row_completeness_status"] == "PASS" for x in case_rows), "row_cannot_verify": sum(x["row_completeness_status"] != "PASS" for x in case_rows),
        "prediction_blind": True, "ocr_read": False, "extractor_read": False, "final_holdout_2_accessed": False,
        "semantic_role_integrity": statuses.get("CANNOT_VERIFY", 0) == 0 and statuses.get("SOURCE_AMBIGUOUS", 0) == 0 and statuses.get("VERIFIED_ERROR", 0) == 0,
        "gold_completeness": all(x["row_completeness_status"] == "PASS" for x in case_rows), "image_layout_review": all(x["image_exists"] for x in case_rows),
    }
    summary["gold_freeze_ready"] = bool(summary["semantic_role_integrity"] and summary["gold_completeness"] and summary["image_layout_review"])
    (output_root / "semantic_evidence_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/fintra/devscale1500/manifest.jsonl"))
    parser.add_argument("--cases-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--old-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--training-root", type=Path, default=Path("artifacts/aihub/Training"))
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.allowlist, args.manifest, args.cases_root, args.gold_root, args.training_root, args.old_root, args.output_root), ensure_ascii=False))


if __name__ == "__main__":
    main()

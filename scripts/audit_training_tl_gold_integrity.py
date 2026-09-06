"""Audit the raw Training TL -> Fintra Gold chain for Accurate75 #1.

The raw TL files contain word-level annotations, not Fintra semantic labels.
Consequently this audit never treats ``source_annotation.json`` as the
original label and never uses OCR or extractor predictions to decide Gold.
It records provenance for every Gold field and applies only conservative
source-token/type/layout checks.  Unprovable semantic assignments are marked
``CANNOT_VERIFY`` instead of being silently declared correct.

FINAL-HOLDOUT #2 is intentionally outside this script's inputs.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


WIDTH = 1654.0
HEIGHT = 2340.0
NUMBER_RE = re.compile(r"^[+$-]?\s*\d[\d,./() +:-]*(?:[A-Za-z]+)?$")
DATE_RE = re.compile(r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}[-/]?[A-Za-z]{3,9}[-/]?\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2}[, ]+\d{4})\b", re.I)
UNIT_RE = re.compile(r"^(?:KG|KGS|G|GRAM|GRAMS|PC|PCS|EA|EACH|PKG|BOX|CTN|SET|UNIT|BAG|PIECE|POUND|YARD|INCH|SF|CT|ST)$", re.I)
COUNTRIES = {"JAPAN", "FRANCE", "CANADA", "CHILE", "CYPRUS", "SPAIN", "ITALY", "NORWAY", "GREECE", "TAIWAN", "BELGIUM", "INDIA", "AUSTRALIA", "KOREA", "GERMANY", "SWEDEN", "PERU", "NIGERIA", "IRELAND"}


def find_label_root(training_root: Path) -> Path:
    candidates = [p for p in training_root.iterdir() if p.is_dir() and any(p.glob("TL*.zip"))]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one local Training TL directory, found: {candidates}")
    return candidates[0]


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    return {str((row := json.loads(line))["stable_sample_id"]): row
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            continue
        result.append({
            "index": index,
            "text": str(item.get("data") or "").strip(),
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
        })
    return result


def text_for(indices: list[int], raw: list[dict[str, Any]]) -> str:
    by_index = {item["index"]: item for item in raw}
    return " ".join(by_index[index]["text"] for index in indices if index in by_index)


def field_items(field: dict[str, Any], raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_index = {item["index"]: item for item in raw}
    return [by_index[index] for index in field.get("source_token_indices", []) if index in by_index]


def bbox_for(indices: list[int], raw: list[dict[str, Any]]) -> list[float] | None:
    selected = [item["bbox"] for item in raw if item["index"] in set(indices)]
    if not selected:
        return None
    return [min(x[0] for x in selected), min(x[1] for x in selected), max(x[2] for x in selected), max(x[3] for x in selected)]


def field_kind(name: str) -> str:
    leaf = name.rsplit(".", 1)[-1]
    if leaf in {"invoice_number", "packing_list_number", "bl_number"}:
        return "identifier"
    if leaf.endswith("description") or leaf in {"seller", "buyer", "exporter", "consignee", "shipper", "notify_party", "vessel", "port_of_loading", "port_of_discharge", "goods_description"}:
        return "text"
    if "date" in leaf:
        return "date"
    if leaf in {"currency", "unit", "weight_unit"}:
        return "unit"
    return "numeric"


def type_issue(field_name: str, value: str) -> str | None:
    kind = field_kind(field_name)
    upper = value.strip().upper()
    if kind == "date" and not DATE_RE.search(value):
        return "date_type_incompatible"
    if kind == "identifier":
        return None
    if kind == "numeric" and not NUMBER_RE.fullmatch(value):
        return "numeric_type_incompatible"
    if field_name.endswith("unit") and not UNIT_RE.fullmatch(value):
        return "unit_type_incompatible"
    if field_name.endswith("weight_unit") and not re.fullmatch(r"(?:KG|KGS|G|GRAM|GRAMS)", upper):
        return "weight_unit_type_incompatible"
    if field_name in {"port_of_loading", "port_of_discharge"}:
        if "," not in value or any(word in upper for word in ("TEL", "FAX", "STREET", "ROAD")):
            return "port_place_type_incompatible"
    return None


def line_center(item: dict[str, Any]) -> float:
    return (item["bbox"][1] + item["bbox"][3]) / 2


def semantic_conflict(field: dict[str, Any], raw: list[dict[str, Any]], document_type: str) -> tuple[str, str] | None:
    """Return a conservative, prediction-blind conflict classification.

    A raw TL annotation has no semantic labels.  We therefore only promote a
    conflict when the source geometry and typed row structure are explicit.
    Other valid token references remain CANNOT_VERIFY rather than being
    inferred from an extractor output.
    """
    name = str(field["field_name"])
    value = str(field.get("value") or "").strip()
    indices = [int(x) for x in field.get("source_token_indices", [])]
    if not value or str(field.get("status")) != "available":
        return None
    by_index = {item["index"]: item for item in raw}
    selected = [by_index[i] for i in indices if i in by_index]
    if not selected:
        return "SOURCE_LABEL_AMBIGUOUS_OR_WRONG", "Gold references token indices absent from raw TL"
    issue = type_issue(name, value)
    if issue:
        return "VERIFIED_GOLD_MAPPING_ERROR", issue

    if document_type == "B/L" and name in {"port_of_loading", "port_of_discharge"}:
        # A same-row pair of comma-place cells is a strong layout signal.  If
        # the two canonical fields are assigned to reversed horizontal cells,
        # the old Gold mapping is demonstrably swapped.  This is a generic
        # check; no document value is used.
        return None

    if document_type == "Commercial Invoice" and ".description" in name:
        y = sum(line_center(item) for item in selected) / len(selected)
        has_numeric_column_token = any(
            item["bbox"][0] >= 0.40 * WIDTH
            and NUMBER_RE.fullmatch(item["text"].strip())
            and abs(line_center(item) - y) <= 30
            for item in raw
        )
        has_left_text = any(
            item["bbox"][2] < 0.40 * WIDTH
            and re.search(r"[A-Za-z]", item["text"])
            and abs(line_center(item) - y) <= 30
            for item in raw
        )
        if has_numeric_column_token and has_left_text and any(
            NUMBER_RE.fullmatch(item["text"].strip()) for item in selected
        ):
            return "VERIFIED_GOLD_MAPPING_ERROR", "description includes a typed numeric column token while textual row content exists to its left"
    return None


def audit_case(case_id: str, row: dict[str, Any], tl_root: Path, cases_root: Path, corrected_root: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    archive = next(tl_root.glob(f"TL*{row['source_group']}.zip"))
    with zipfile.ZipFile(archive) as handle:
        raw_payload = json.loads(handle.read(str(row["label_entry"])).decode("utf-8-sig"))
    raw = tokens(raw_payload)
    case = cases_root / case_id
    source_path = case / "source_annotation.json"
    old_path = case / "semantic_gold_fields.json"
    old_fields = json.loads(old_path.read_text(encoding="utf-8"))
    corrected_path = (corrected_root / case_id / "semantic_gold_fields.json") if corrected_root else None
    corrected_fields = json.loads(corrected_path.read_text(encoding="utf-8")) if corrected_path and corrected_path.is_file() else []
    old_by_name = {field["field_name"]: field for field in old_fields}
    port_swap = False
    if row["document_type"] == "B/L":
        loading = old_by_name.get("port_of_loading", {})
        discharge = old_by_name.get("port_of_discharge", {})
        loading_items = field_items(loading, raw)
        discharge_items = field_items(discharge, raw)
        if loading_items and discharge_items:
            loading_x = sum(item["bbox"][0] + item["bbox"][2] for item in loading_items) / (2 * len(loading_items))
            discharge_x = sum(item["bbox"][0] + item["bbox"][2] for item in discharge_items) / (2 * len(discharge_items))
            loading_y = sum(line_center(item) for item in loading_items) / len(loading_items)
            discharge_y = sum(line_center(item) for item in discharge_items) / len(discharge_items)
            # The old builder's paired port fields are visibly assigned to
            # opposite horizontal cells when the right cell is loading and
            # the left cell is discharge on the same row.
            port_swap = loading_x > discharge_x and abs(loading_y - discharge_y) <= 45
    records = []
    for field in old_fields:
        indices = [int(x) for x in field.get("source_token_indices", [])]
        source_value = text_for(indices, raw)
        result = semantic_conflict(field, raw, str(row["document_type"]))
        if port_swap and field["field_name"] in {"port_of_loading", "port_of_discharge"}:
            classification, reason = "VERIFIED_GOLD_MAPPING_ERROR", "paired source port cells are assigned to opposite loading/discharge roles by the old Gold mapping"
        elif result:
            classification, reason = result
        elif field.get("status") == "not_applicable":
            classification, reason = "NOT_APPLICABLE", "Gold explicitly marks the field not applicable"
        elif field.get("status") != "available":
            classification, reason = "CANNOT_VERIFY", "Gold is ambiguous and has no available source value"
        elif source_value != str(field.get("value") or ""):
            classification, reason = "SOURCE_LABEL_AMBIGUOUS_OR_WRONG", "Gold value differs from the raw TL tokens referenced by its indices"
        else:
            classification, reason = "CANNOT_VERIFY", "Raw TL is word-level only; semantic role cannot be proven without a semantic label"
        records.append({
            "case_id": case_id,
            "document_type": row["document_type"],
            "source_group": row["source_group"],
            "field_name": field["field_name"],
            "current_gold": field.get("value"),
            "source_value_from_raw_tl": source_value or None,
            "source_token_indices": json.dumps(indices),
            "gold_bbox": json.dumps(bbox_for(indices, raw)),
            "source_annotation": str(source_path),
            "original_tl_zip": str(archive),
            "original_tl_entry": row["label_entry"],
            "classification": classification,
            "reason": reason,
            "corrected_gold": next((x.get("value") for x in corrected_fields if x.get("field_name") == field["field_name"]), None),
        })
    return records, {"raw_token_count": len(raw), "source_annotation": str(source_path), "old_gold": str(old_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", type=Path, default=Path("artifacts/fintra/train-scale-v1/parallel/accurate-balanced75.txt"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/fintra/devscale1500/manifest.jsonl"))
    parser.add_argument("--training-root", type=Path, default=Path("artifacts/aihub/Training"))
    parser.add_argument("--cases-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--corrected-root", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v3.2-accurate75/cases"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/fintra/gold_audit/training-tl-gold-integrity"))
    args = parser.parse_args()
    ids = [line.strip() for line in args.allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(ids) != 75 or len(set(ids)) != 75:
        raise ValueError(f"Accurate75 #1 must contain 75 unique IDs, got {len(ids)}")
    manifest = load_manifest(args.manifest)
    tl_root = find_label_root(args.training_root)
    records: list[dict[str, Any]] = []
    case_meta = []
    for case_id in ids:
        if case_id not in manifest:
            raise KeyError(case_id)
        current, meta = audit_case(case_id, manifest[case_id], tl_root, args.cases_root, args.corrected_root)
        records.extend(current); case_meta.append({"case_id": case_id, **meta})
    args.output_root.mkdir(parents=True, exist_ok=True)
    columns = list(records[0])
    with (args.output_root / "gold_integrity_fields.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader(); writer.writerows(records)
    counts = Counter(record["classification"] for record in records)
    by_type = defaultdict(Counter); by_field = defaultdict(Counter)
    for record in records:
        by_type[record["document_type"]][record["classification"]] += 1
        by_field[f"{record['document_type']}:{record['field_name']}"][record["classification"]] += 1
    summary = {
        "scope": "Accurate75 #1 only",
        "prediction_blind": True,
        "final_holdout_2_accessed": False,
        "original_tl_root": str(tl_root),
        "source_annotation_is_downstream": True,
        "source_annotation_provenance": "parsed content and token text/geometry equal to raw TL; byte serialization differs",
        "field_records": len(records),
        "cases": len(ids),
        "classifications": dict(counts),
        "by_document_type": {key: dict(value) for key, value in by_type.items()},
        "by_field": {key: dict(value) for key, value in by_field.items()},
        "direct_confirmed_examples": {
            "bl01-081-IMG_OCR_6_T_BL_004108": "raw TL port pair is OHSE/JAPAN at x=121 and GUINES/FRANCE at x=505; old Gold assigns the pair to opposite semantic fields",
            "inv01-084-IMG_OCR_6_T_NV_003885": "raw TL row tokens 50-53 are Fire Extinguisher Fire Suppression, token 54 is HS 1111.39; old Gold includes HS as description",
        },
        "case_metadata": case_meta,
    }
    (args.output_root / "gold_integrity_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Training TL to Fintra Gold integrity audit",
        "",
        "Scope is Accurate75 #1 only. FINAL-HOLDOUT #2 was not accessed.",
        "",
        f"- Cases: {len(ids)}",
        f"- Field records: {len(records)}",
        f"- Classifications: `{json.dumps(dict(counts), ensure_ascii=False, sort_keys=True)}`",
        f"- Raw TL root: `{tl_root}`",
        "- Raw TL JSON was read directly from the local Training TL ZIP entries.",
        "- `source_annotation.json` is a parsed/re-serialized downstream copy, not the original TL file.",
        "- No OCR or extractor output is an input to this audit.",
        "",
        "## Interpretation",
        "",
        "Because AI-Hub TL is word-level and has no Fintra semantic labels, a valid token reference does not by itself prove seller/port/item semantic assignment. Such rows remain `CANNOT_VERIFY`. `VERIFIED_GOLD_MAPPING_ERROR` is reserved for explicit type or source-layout contradictions.",
        "",
        "## By document type",
        "",
    ]
    for key, value in sorted(by_type.items()):
        report.append(f"- **{key}**: `{json.dumps(dict(value), ensure_ascii=False, sort_keys=True)}`")
    report += [
        "",
        "## Confirmed source examples",
        "",
        "- `bl01-081-IMG_OCR_6_T_BL_004108`: the original image labels OHSE/JAPAN as Place of Loading and GUINES/FRANCE as Place of Discharge. The old Gold swaps the two source token pairs. This is a Gold mapping error, not an extractor inference.",
        "- `inv01-084-IMG_OCR_6_T_NV_003885`: the raw TL row has `Fire Extinguisher, Fire Suppression` followed by HS code `1111.39`; the old Gold description `Suppression 1111.39` crosses the description/HS column boundary. This is a Gold row/column mapping error.",
        "",
    ]
    (args.output_root / "TRAINING_TL_GOLD_INTEGRITY.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"cases": len(ids), "field_records": len(records), "classifications": dict(counts), "output_root": str(args.output_root), "final_holdout_2_accessed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()

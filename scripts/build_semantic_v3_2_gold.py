"""Build a corrected, prediction-blind semantic Gold candidate.

This version is deliberately separate from semantic-v3/v3.1.  It fixes two
general mapping defects found by direct comparison with the local AI-Hub
Training TL archives: B/L loading/discharge left-right inversion and CI item
rows being seeded by unrelated numeric text above the item table.  It reads
only source annotations and case manifests; it never reads OCR or extractor
predictions.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import build_semantic_v3_gold as v3
from build_semantic_field_gold import _lines, _join, _evidence, _numeric


MONEY_RE = re.compile(r"^[+$€£¥]?\s*\d[\d,]*(?:\.\d+)?$")
UNIT_WORDS = {
    "KG", "KGS", "G", "GRAM", "GRAMS", "PC", "PCS", "EA", "EACH", "PKG",
    "BOX", "CTN", "SET", "UNIT", "POUND", "YARD", "DRUM", "BAG", "PIECE", "ST",
}
TRANSPORT_TERMS = {"FOB", "CIF", "CFR", "DAF", "DDP", "DDU", "DEQ", "CFS", "CY"}


def _numeric_token(token: dict[str, Any]) -> bool:
    return bool(MONEY_RE.fullmatch(token["text"].strip())) or _numeric(token["text"])


def _unit_token(token: dict[str, Any]) -> bool:
    text = token["text"].strip()
    if text.upper() in UNIT_WORDS:
        return True
    return bool(re.fullmatch(r"[A-Za-z]+", text)) or bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s+[A-Za-z]+", text))


def _quantity_unit_cells(line: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None, str | None]:
    """Resolve a quantity/unit pair before considering HS or price numbers."""
    combined: list[tuple[dict[str, Any], str, str]] = []
    units = []
    numbers = []
    for token in line:
        if not (.30 * v3.v2.WIDTH <= token["bbox"][0] <= .68 * v3.v2.WIDTH):
            continue
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s+([A-Za-z]+)", token["text"].strip())
        if match:
            combined.append((token, match.group(1), match.group(2)))
        elif token["text"].strip().upper() in UNIT_WORDS or re.fullmatch(r"[A-Za-z]+", token["text"].strip()):
            units.append(token)
        elif _numeric_token(token):
            numbers.append(token)
    if combined:
        token, quantity, unit = combined[0]
        return [token], [token], quantity, unit
    if not numbers:
        return [], [], None, None
    if not units:
        quantity = min(numbers, key=lambda candidate: candidate["bbox"][0])
        return [quantity], [], quantity["text"].strip(), None
    # In templates with an HS-code column, the quantity is the numeric token
    # nearest to the unit, not the leftmost decimal number in the row.
    unit = min(units, key=lambda candidate: min(abs(candidate["bbox"][0] - number["bbox"][0]) for number in numbers))
    quantity = min(numbers, key=lambda candidate: abs(candidate["bbox"][0] - unit["bbox"][0]))
    if abs(quantity["bbox"][0] - unit["bbox"][0]) > 140.0:
        quantity = min(numbers, key=lambda candidate: candidate["bbox"][0])
        return [quantity], [], quantity["text"].strip(), None
    return [quantity], [unit], quantity["text"].strip(), unit["text"].strip()


def _identifier_like(text: str) -> bool:
    # Generic marks/HS-like identifiers are excluded from textual description
    # only when a real alphabetic description is also present on the row.
    return bool(re.fullmatch(r"[A-Za-z]*\d[A-Za-z0-9./_-]*", text.strip()))


def _port_address_like(text: str) -> bool:
    upper = text.upper()
    return (
        bool(re.search(r"\b(?:STREET|ROAD|AVENUE|BOULEVARD|DISTRICT|SUITE|BLVD|RD|AVE)\b", upper))
        or bool(re.search(r"\b\d{3,}\b", text))
        or bool(re.search(r"\b[A-Z]\d[A-Z]\s*\d[A-Z]\d\b", upper))
    )


def _row_seeds(tokens: list[dict[str, Any]]) -> list[float]:
    """Find table rows from quantity-column numbers plus right-side numbers."""
    seeds: list[float] = []
    for line in _lines([x for x in tokens if 850 <= x["bbox"][1] <= 1750], tolerance=18.0):
        numeric = [x for x in line if .30 * v3.v2.WIDTH <= x["bbox"][0] <= .68 * v3.v2.WIDTH and _numeric_token(x)]
        right_numeric = [x for x in line if x["bbox"][0] > .60 * v3.v2.WIDTH and _numeric_token(x)]
        if numeric and right_numeric:
            center = sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in line) / len(line)
            if not seeds or center - seeds[-1] > 45.0:
                seeds.append(center)
    return seeds


def _row_tokens(tokens: list[dict[str, Any]], center: float, next_center: float | None) -> list[dict[str, Any]]:
    # Include a possible wrapped description line before the next typed row,
    # but do not absorb a distant footer or a prior non-table section.
    upper = next_center - 20.0 if next_center is not None else center + 115.0
    return [
        x for x in tokens
        if 850 <= x["bbox"][1] <= 1750
        and center - 46.0 <= (x["bbox"][1] + x["bbox"][3]) / 2 <= upper
    ]


def _description(field_name: str, row: list[dict[str, Any]], quantity_x: float | None) -> dict[str, Any]:
    if quantity_x is None:
        return _evidence(field_name, [], status="ambiguous_gt", review="no_typed_quantity_unit_anchor_for_description")
    candidates = [
        x for x in row
        if x["bbox"][2] < quantity_x
        and re.search(r"[A-Za-z]", x["text"])
        and not _identifier_like(x["text"])
        and x["text"].strip().upper() not in UNIT_WORDS
    ]
    # If marks/HS-like tokens are mixed with a real description, retain the
    # textual portion only.  This is type/layout logic, not case knowledge.
    if not candidates:
        return _evidence(field_name, [], status="ambiguous_gt", review="description_has_no_textual_candidate_before_quantity_unit")
    return _evidence(field_name, sorted(candidates, key=lambda x: (x["bbox"][1], x["bbox"][0], x["index"])), review="typed_row_remaining_text_before_quantity_unit")


def _ci_table_v2(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table_tokens = [x for x in tokens if 850 <= x["bbox"][1] <= 1750]
    seeds = _row_seeds(table_tokens)
    fields: list[dict[str, Any]] = []
    for index, center in enumerate(seeds):
        row = _row_tokens(table_tokens, center, seeds[index + 1] if index + 1 < len(seeds) else None)
        row_lines = _lines(row, tolerance=18.0)
        seed_line = min(row_lines, key=lambda line: abs(sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in line) / len(line) - center))
        quantity, unit, quantity_value, unit_value = _quantity_unit_cells(row)
        quantity_x = min((x["bbox"][0] for x in quantity + unit), default=None)
        cluster_right = max((x["bbox"][2] for x in quantity + unit), default=quantity_x)
        after = sorted((x for x in row if cluster_right is not None and x["bbox"][0] > cluster_right and _numeric_token(x)), key=lambda x: (x["bbox"][0], x["index"]))
        # The first two typed numeric cells after quantity/unit are the
        # left-to-right price and amount cells.  Later identifier-like values
        # are not treated as money unless no better pair exists.
        monetary = [x for x in after if MONEY_RE.fullmatch(x["text"].strip()) or "." in x["text"] or "," in x["text"]]
        if len(monetary) < 2:
            monetary = after
        price = monetary[:1]
        amount = monetary[1:2]
        fields.extend([
            _description(f"items[{index}].description", row, quantity_x),
            _evidence(f"items[{index}].quantity", quantity[:1], value=quantity_value, status="available" if quantity else "ambiguous_gt", review="typed_quantity_from_row_anchor"),
            _evidence(f"items[{index}].unit", unit[:1], value=unit_value, status="available" if unit else "ambiguous_gt", review="typed_unit_from_row_anchor"),
            _evidence(f"items[{index}].unit_price", price, status="available" if len(price) == 1 else "ambiguous_gt", review="left_typed_numeric_after_quantity_unit"),
            _evidence(f"items[{index}].amount", amount, status="available" if len(amount) == 1 else "ambiguous_gt", review="right_typed_numeric_after_quantity_unit"),
        ])
    return fields


def _vessel_v2(tokens: list[dict[str, Any]]) -> dict[str, Any]:
    items = [x for x in tokens if .02 * v3.v2.WIDTH <= x["bbox"][0] and x["bbox"][2] <= .30 * v3.v2.WIDTH and .35 * v3.v2.HEIGHT <= x["bbox"][1] <= .55 * v3.v2.HEIGHT]
    for line in v3.v2._lines(items):
        text = v3.v2._join(line)
        upper = text.upper().strip()
        words = set(re.findall(r"[A-Z][A-Z.'-]*", upper))
        if not text or "," in text or v3._is_country(text) or v3._is_phone(text) or words.intersection(TRANSPORT_TERMS) or re.search(r"\bV\s*\.?\s*\d+\b", upper):
            continue
        if re.search(r"[A-Za-z]", text):
            return v3.v2._evidence("vessel", line, review="typed_vessel_anchor_excluding_transport_terms")
    return v3.v2._evidence("vessel", [], status="ambiguous_gt", review="no_unique_typed_vessel_candidate")


def _party_v2(field_name: str, tokens: list[dict[str, Any]], document_type: str, ordinal: int) -> dict[str, Any]:
    lines = []
    for line in v3._party_lines(tokens, document_type):
        text = v3.v2._join(line).upper().strip()
        if re.search(r"\bV\s*\.?\s*\d+\b", text):
            continue
        if set(re.findall(r"[A-Z][A-Z.'-]*", text)).intersection(TRANSPORT_TERMS):
            continue
        lines.append(line)
    if ordinal >= len(lines):
        return v3.v2._evidence(field_name, [], status="ambiguous_gt", review="party_block_has_no_unique_typed_company_line")
    return v3.v2._evidence(field_name, lines[ordinal], review="relative_party_block_and_typed_company_line")


def _port_segments(tokens: list[dict[str, Any]], target_y: float | None) -> list[list[dict[str, Any]]]:
    """Split a port row into horizontal cells before assigning semantic roles."""
    candidates: list[tuple[float, float, list[dict[str, Any]]]] = []
    items = [x for x in tokens if .05 * v3.v2.HEIGHT <= x["bbox"][1] <= .58 * v3.v2.HEIGHT]
    for line in v3.v2._lines(items):
        segments: list[list[dict[str, Any]]] = []
        for token in line:
            if not segments or token["bbox"][0] - segments[-1][-1]["bbox"][2] > 70.0:
                segments.append([token])
            else:
                segments[-1].append(token)
        for segment in segments:
            text = v3.v2._join(segment)
            upper = text.upper()
            if "," not in text or text.count(",") != 1 or v3._is_country(text) or v3._is_phone(text) or _port_address_like(text):
                continue
            if set(re.findall(r"[A-Z][A-Z.'-]*", upper)).intersection(TRANSPORT_TERMS):
                continue
            cy = sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in segment) / len(segment)
            distance = abs(cy - target_y) if target_y is not None else cy
            if target_y is not None and distance > 180.0:
                continue
            candidates.append((distance, min(x["bbox"][0] for x in segment), segment))
    if not candidates:
        return []
    # Keep all typed place cells.  The port-pair resolver uses vessel-relative
    # geometry to distinguish stacked ports from Place of Receipt/Delivery.
    return [item[2] for item in sorted(candidates, key=lambda item: (item[0], item[1]))]


def _port_pair(tokens: list[dict[str, Any]], vessel_tokens: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    vessel_center = sum((x["bbox"][0] + x["bbox"][2]) / 2 for x in vessel_tokens) / len(vessel_tokens) if vessel_tokens else .25 * v3.v2.WIDTH
    vessel_y = sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in vessel_tokens) / len(vessel_tokens) if vessel_tokens else None
    candidates = _port_segments(tokens, vessel_y)
    if len(candidates) < 2:
        return (candidates[0], []) if candidates else ([], [])
    centers = [
        (
            sum(x["bbox"][0] + x["bbox"][2] for x in segment) / (2 * len(segment)),
            sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in segment) / len(segment),
            segment,
        )
        for segment in candidates
    ]
    # Some templates stack loading/discharge in one column.  Prefer that pair
    # over nearby Place of Receipt/Delivery cells.
    groups: list[list[tuple[float, float, list[dict[str, Any]]]]] = []
    for center, y_center, segment in sorted(centers):
        if not groups or center - groups[-1][-1][0] > 180.0 or abs(y_center - groups[-1][-1][1]) > 140.0:
            groups.append([(center, y_center, segment)])
        else:
            groups[-1].append((center, y_center, segment))
    repeated = [group for group in groups if len(group) >= 2]
    if repeated:
        chosen = min(repeated, key=lambda group: abs(sum(item[0] for item in group) / len(group) - vessel_center))
        # A repeated left-side block is normally Place of Receipt/other party
        # text in these forms.  Without an annotated semantic label, keeping
        # it as a port would invent a role from geometry alone.
        vessel_right = max((x["bbox"][2] for x in vessel_tokens), default=vessel_center)
        if sum(item[0] for item in chosen) / len(chosen) < vessel_center or max(item[0] for item in chosen) < vessel_right + 30.0:
            return [], []
        pair = [item[2] for item in sorted(chosen, key=lambda item: item[1])[:2]]
        return pair[0], pair[1]
    nearest = sorted(centers, key=lambda item: abs(item[0] - vessel_center))[:2]
    nearest = [item[2] for item in nearest]
    if vessel_y is not None:
        y_values = [sum((x["bbox"][1] + x["bbox"][3]) / 2 for x in segment) / len(segment) for segment in nearest]
        if abs(y_values[0] - y_values[1]) > 35.0 and min(y_values) <= vessel_y <= max(y_values):
            above, below = sorted(zip(y_values, nearest), key=lambda item: item[0])
            return above[1], below[1]
    nearest.sort(key=lambda segment: min(x["bbox"][0] for x in segment))
    return nearest[0], nearest[1]


def build_v3_2(payload: dict[str, Any], document_type: str) -> list[dict[str, Any]]:
    tokens = v3.v2._tokens(payload)
    fields = v3.build_v3(payload, document_type)
    replacements: dict[str, dict[str, Any]] = {}
    if document_type == "Commercial Invoice":
        replacements["seller"] = _party_v2("seller", tokens, document_type, 0)
        replacements["buyer"] = _party_v2("buyer", tokens, document_type, 1)
        # Keep the audited Gold schema's item cardinality.  The corrected
        # table resolver may discover more candidate rows than this case's
        # reviewed schema; silently adding those rows would change the
        # denominator rather than correct a mapping.
        item_names = {field["field_name"] for field in fields if field["field_name"].startswith("items[")}
        fields = [field for field in fields if not field["field_name"].startswith("items[")]
        fields.extend(field for field in _ci_table_v2(tokens) if field["field_name"] in item_names)
        return [replacements.get(field["field_name"], field) for field in fields]
    if document_type == "Packing List":
        replacements["exporter"] = _party_v2("exporter", tokens, document_type, 0)
        replacements["consignee"] = _party_v2("consignee", tokens, document_type, 1)
        return [replacements.get(field["field_name"], field) for field in fields]

    for name, ordinal in (("shipper", 0), ("consignee", 1), ("notify_party", 2)):
        replacements[name] = _party_v2(name, tokens, document_type, ordinal)
    replacements["vessel"] = _vessel_v2(tokens)
    vessel_indices = set(replacements["vessel"].get("source_token_indices", []))
    vessel_tokens = [token for token in tokens if token["index"] in vessel_indices]
    vessel_y = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in vessel_tokens) / len(vessel_tokens) if vessel_tokens else None
    loading, discharge = _port_pair(tokens, vessel_tokens)
    replacements["port_of_loading"] = v3.v2._evidence("port_of_loading", loading, review="anchor_relative_port_layout_loading") if loading else v3.v2._evidence("port_of_loading", [], status="ambiguous_gt", review="no_unique_loading_place_cell")
    replacements["port_of_discharge"] = v3.v2._evidence("port_of_discharge", discharge, review="anchor_relative_port_layout_discharge") if discharge else v3.v2._evidence("port_of_discharge", [], status="ambiguous_gt", review="no_unique_discharge_place_cell")
    return [replacements.get(field["field_name"], field) for field in fields]


def _case_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def build(cases_root: Path, allowlist: Path, output_root: Path, old_root: Path, diff_path: Path) -> dict[str, Any]:
    allowed = _case_ids(allowlist)
    if len(allowed) != len(set(allowed)):
        raise ValueError("allowlist contains duplicate case IDs")
    out_cases = output_root / "cases"
    out_cases.mkdir(parents=True, exist_ok=True)
    changes: list[dict[str, Any]] = []
    processed = 0
    for case_id in allowed:
        source_case = cases_root / case_id
        manifest_path = source_case / "case_manifest.json"
        source_path = source_case / "source_annotation.json"
        old_path = old_root / case_id / "semantic_gold_fields.json"
        if not all(path.is_file() for path in (manifest_path, source_path, old_path)):
            raise FileNotFoundError(f"missing source/old Gold for {case_id}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        fields = build_v3_2(json.loads(source_path.read_text(encoding="utf-8")), manifest["document_type"])
        target = out_cases / case_id
        target.mkdir(parents=True, exist_ok=True)
        (target / "case_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "semantic_gold_fields.json").write_text(json.dumps(fields, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        old = {x["field_name"]: x for x in json.loads(old_path.read_text(encoding="utf-8"))}
        new = {x["field_name"]: x for x in fields}
        for name in sorted(set(old) | set(new)):
            before, after = old.get(name, {}), new.get(name, {})
            keys = ("value", "status", "source_token_indices")
            if all(before.get(k) == after.get(k) for k in keys):
                continue
            changes.append({
                "case_id": case_id,
                "document_type": manifest["document_type"],
                "field_name": name,
                "old_gold": before.get("value"),
                "new_gold": after.get("value"),
                "old_status": before.get("status"),
                "new_status": after.get("status"),
                "old_source_token_indices": json.dumps(before.get("source_token_indices", [])),
                "new_source_token_indices": json.dumps(after.get("source_token_indices", [])),
                "source_token_indices_changed": before.get("source_token_indices", []) != after.get("source_token_indices", []),
                "change_reason": after.get("gold_review", "semantic-v3.2 generalized rule"),
            })
        processed += 1
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(changes[0]) if changes else ["case_id", "document_type", "field_name"]
    with diff_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(changes)
    summary = {"cases": processed, "changed_fields": len(changes), "allowlist": str(allowlist), "gold_root": str(out_cases), "diff": str(diff_path), "prediction_blind": True}
    (output_root / "gold_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--allowlist", type=Path, default=Path("artifacts/fintra/train-scale-v1/parallel/accurate-balanced75.txt"))
    parser.add_argument("--old-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v3.2-accurate75"))
    parser.add_argument("--diff", type=Path, default=Path("artifacts/fintra/gold_audit/v3.1_to_v3.2_accurate75_diff.csv"))
    args = parser.parse_args()
    print(json.dumps(build(args.cases_root, args.allowlist, args.output_root, args.old_root, args.diff), ensure_ascii=False))


if __name__ == "__main__":
    main()

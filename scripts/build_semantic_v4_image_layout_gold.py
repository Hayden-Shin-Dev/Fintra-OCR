"""Regenerate prediction-blind Gold using original-image layout evidence.

The AI-Hub Training TL supplies the value words and their polygons, while the
source image supplies the ruled party/table structure omitted from the TL.
Only values that pass both independent sources are ``available``.  Everything
else is conservatively emitted as ``ambiguous_gt``; this script never reads
Paddle/Modern OCR or extractor output.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import build_semantic_v3_gold as v3  # noqa: E402
import build_semantic_v3_2_gold as v32  # noqa: E402
from build_semantic_field_gold import _evidence, _join, _lines  # noqa: E402
from image_layout_semantics import Grid, detect_grid, inside, party_zone, table_row_inventory  # noqa: E402


UNIT_WORDS = v32.UNIT_WORDS
UNIT_STOP_WORDS = {"FOR", "OF", "THE", "AND", "OR", "TO", "IN", "BY", "ON"}
TRANSPORT_TERMS = v32.TRANSPORT_TERMS
ADDRESS_WORDS = {
    "STREET", "ST", "ROAD", "RD", "DR", "AVENUE", "AVE", "BLVD", "BOULEVARD", "SUITE", "RM", "ROOM",
    "PHONE", "TEL", "FAX", "MOBILE", "POSTAL", "ZIP", "COUNTRY", "KOREA", "JAPAN", "CHINA",
    "CANADA", "AUSTRALIA", "UNITED", "STATES", "FRANCE", "ITALY", "SPAIN", "INDIA", "SUDAN",
}
COMPANY_WORDS = {"CO", "CO.", "LTD", "LTD.", "INC", "INC.", "CORP", "CORP.", "COMPANY", "HOLDINGS", "ENTERPRISES", "INDUSTRY", "TRADING", "SOLUTIONS"}
COUNTRY_WORDS = {
    "ARGENTINA", "AUSTRALIA", "BELGIUM", "BRAZIL", "CANADA", "CHILE", "CHINA", "CYPRUS", "DENMARK", "EGYPT", "FINLAND", "FRANCE", "GERMANY", "GREECE", "HAITI", "INDIA", "IRELAND", "ISRAEL", "ITALY", "JAPAN", "KOREA", "MALAYSIA", "MEXICO", "NIGERIA", "NORWAY", "POLAND", "PORTUGAL", "SOUTH", "AFRICA", "SPAIN", "TAIWAN", "THAILAND", "TURKEY", "UNITED", "KINGDOM", "STATES", "VIETNAM", "VIET", "NAM",
}
NUMBER_RE = re.compile(r"^[+$€£¥]?\s*\d[\d,]*(?:\.\d+)?(?:\s*(?:KG|KGS|PKG|PCS|CTN))?$", re.I)
DATE_RE = re.compile(r"(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s*[-,]?\s*\d{1,2}[-,]?\s*\d{2,4})", re.I)
UNIT_RE = re.compile(r"[A-Za-z]{1,8}(?:/[A-Za-z]{1,8})?$")


def _box(tokens: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    return (min(item["bbox"][0] for item in tokens), min(item["bbox"][1] for item in tokens), max(item["bbox"][2] for item in tokens), max(item["bbox"][3] for item in tokens))


def _ambiguous(name: str, reason: str) -> dict[str, Any]:
    return _evidence(name, [], status="ambiguous_gt", review=reason)


def _image_evidence(name: str, tokens: list[dict[str, Any]], grid: Grid, role: str, reason: str, *, value: str | None = None) -> dict[str, Any]:
    value_box = _box(tokens)
    # A zero-area TL polygon cannot be tied back to visible image ink.  It
    # stays ambiguous instead of silently entering an available denominator.
    if value_box[2] - value_box[0] < 1 or value_box[3] - value_box[1] < 1:
        return _ambiguous(name, "source_token_geometry_is_not_renderable_on_original_image")
    field = _evidence(name, tokens, value=value, review=reason)
    field["semantic_evidence"] = {
        "source": "original_image_and_training_tl",
        "method": "ruled_layout_and_typed_token_relation_v1",
        "role": role,
        "image_table": list(grid.table) if grid.table else None,
        "image_columns": list(grid.columns),
        "value_box": list(value_box),
    }
    return field


def _is_number(text: str) -> bool:
    return bool(NUMBER_RE.fullmatch(text.strip()))


def _is_money(text: str) -> bool:
    text = text.strip()
    return _is_number(text) and ("." in text or "," in text or any(symbol in text for symbol in "$€£¥"))


def _is_phone_or_address(text: str) -> bool:
    words = set(re.findall(r"[A-Z]+", text.upper()))
    return (
        bool(words.intersection(ADDRESS_WORDS))
        or bool(re.search(r"(?:TEL|FAX|PHONE|MOBILE|\+\d|\d{3,}[-\s]\d)", text.upper()))
        or bool(re.search(r"[\w.+-]+@[\w.-]+", text))
    )


def _party_lines(tokens: list[dict[str, Any]], grid: Grid, *, full_width: bool = False) -> list[list[dict[str, Any]]]:
    zone = party_zone(grid)
    if zone is None:
        return []
    if full_width:
        zone = (0.0, zone[1], float(grid.width), zone[3])
    candidates: list[list[dict[str, Any]]] = []
    # Split the column before grouping lines.  Header/value rows often place
    # an unrelated right-column value at the exact same y-coordinate; grouping
    # the whole page first would make the left party line appear out of scope.
    scoped = [token for token in tokens if inside(tuple(token["bbox"]), zone, margin=8)]
    for line in _lines(scoped, tolerance=.012 * grid.height):
        if not line:
            continue
        # A CI may print buyer and seller on the same visual row.  Split only
        # a clearly separated full-width line into horizontal components; the
        # normal left-column path keeps ordinary multi-word lines intact.
        components: list[list[dict[str, Any]]] = [line]
        if full_width:
            split: list[list[dict[str, Any]]] = []
            for token in sorted(line, key=lambda item: (item["bbox"][0], item["index"])):
                if not split or token["bbox"][0] - max(item["bbox"][2] for item in split[-1]) > .06 * grid.width:
                    split.append([token])
                else:
                    split[-1].append(token)
            components = split
        for component in components:
            text = _join(component).strip()
            upper = text.upper()
            words = set(re.findall(r"[A-Z]+", upper))
            if (len(re.sub(r"[^A-Za-z]", "", text)) < 5 or _is_phone_or_address(text)
                    or re.match(r"^\s*\d", text)):
                continue
            # A party candidate that contains a country/region word but no
            # organization marker is overwhelmingly an address/country line.
            # Reject it before ordinal role assignment so a missing company does
            # not shift the next party into the wrong role.
            if words.intersection(COUNTRY_WORDS) and not words.intersection(COMPANY_WORDS):
                continue
            if words.intersection(TRANSPORT_TERMS) or DATE_RE.search(text) or _is_number(text):
                continue
            # Organization-like lines can lack a suffix (e.g. GELIVERLEAN
            # HOLDINGS), but must contain multiple alphabetic words or a company
            # marker.  This rejects country/address-only lines without using a
            # document-specific name.
            if not words.intersection(COMPANY_WORDS) and len(re.findall(r"[A-Za-z]+", text)) < 2:
                continue
            candidates.append(component)
    return sorted(candidates, key=lambda line: (_box(line)[1], _box(line)[0]))


def _ci_party_fields(tokens: list[dict[str, Any]], grid: Grid) -> dict[str, dict[str, Any]]:
    """Resolve only visually supported CI party layouts.

    Some invoice templates stack parties in one left block; others print two
    organizations on one row in left/right blocks.  The latter is detected
    from the candidate geometry itself, so the role assignment does not depend
    on a case, literal value, or fixed document coordinate.
    """
    found = _party_lines(tokens, grid, full_width=True)
    left = [line for line in found if (_box(line)[0] + _box(line)[2]) / 2 < .5 * grid.width]
    right = [line for line in found if (_box(line)[0] + _box(line)[2]) / 2 >= .5 * grid.width]
    pair: tuple[list[dict[str, Any]], list[dict[str, Any]]] | None = None
    best_key: tuple[float, float] | None = None
    for left_line in left:
        left_box = _box(left_line)
        left_center_y = (left_box[1] + left_box[3]) / 2
        for right_line in right:
            right_box = _box(right_line)
            right_center_y = (right_box[1] + right_box[3]) / 2
            delta = abs(left_center_y - right_center_y)
            if delta > .035 * grid.height:
                continue
            key = (max(left_box[1], right_box[1]), delta)
            if best_key is None or key < best_key:
                best_key = key
                pair = (left_line, right_line)
    if pair is not None:
        buyer, seller = pair
        return {
            "buyer": _image_evidence("buyer", buyer, grid, "ci_side_by_side_party_block", "image_side_by_side_party_blocks_left_buyer_right_seller"),
            "seller": _image_evidence("seller", seller, grid, "ci_side_by_side_party_block", "image_side_by_side_party_blocks_left_buyer_right_seller"),
        }

    if left:
        return {"seller": _image_evidence("seller", left[0], grid, "party_block", "image_stacked_party_block_first_organization")}
    return {"seller": _ambiguous("seller", "image_party_block_has_no_unique_organization_line")}


def _party_fields(doc_type: str, tokens: list[dict[str, Any]], grid: Grid) -> dict[str, dict[str, Any]]:
    if doc_type == "Commercial Invoice":
        return _ci_party_fields(tokens, grid)
    found = _party_lines(tokens, grid)
    if doc_type == "Packing List":
        names = [("exporter", 0), ("consignee", 1)]
    else:
        names = [("shipper", 0), ("consignee", 1), ("notify_party", 2)]
    result = {}
    for name, index in names:
        if index >= len(found):
            result[name] = _ambiguous(name, "image_party_block_has_no_unique_organization_line")
        else:
            result[name] = _image_evidence(name, found[index], grid, "party_block", "image_ruled_party_block_and_organization_line")
    return result


def _table_lines(tokens: list[dict[str, Any]], grid: Grid) -> list[list[dict[str, Any]]]:
    if grid.table is None:
        return []
    region = grid.table
    included = [token for token in tokens if inside(tuple(token["bbox"]), region, margin=5)]
    return _lines(included, tolerance=.014 * grid.height)


def _row_groups(lines: list[list[dict[str, Any]]], grid: Grid, *, min_money: int) -> list[list[dict[str, Any]]]:
    """Use independent typed evidence to construct real table rows."""
    seeds: list[int] = []
    for index, line in enumerate(lines):
        money = sum(_is_money(token["text"]) for token in line)
        alpha = sum(bool(re.search(r"[A-Za-z]", token["text"])) for token in line)
        if money >= min_money and alpha:
            seeds.append(index)
    rows: list[list[dict[str, Any]]] = []
    for position, start in enumerate(seeds):
        end = seeds[position + 1] if position + 1 < len(seeds) else len(lines)
        row = [token for line in lines[start:end] for token in line]
        if row:
            rows.append(row)
    return rows


def _rightmost_money(row: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = sorted((token for token in row if _is_money(token["text"])), key=lambda token: (token["bbox"][0], token["index"]))
    return candidates[-2:]


def _quantity_unit(row: list[dict[str, Any]], monetary: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    limit = min((token["bbox"][0] for token in monetary), default=float("inf"))
    numbers = [token for token in row if token["bbox"][0] < limit and re.fullmatch(r"\d+(?:[.,]\d+)?", token["text"].strip())]
    # A printed unit cell is often an open-vocabulary abbreviation (for
    # example CT, DOZ, LB) and the source list does not exhaust every valid
    # unit.  Keep the typed constraint (a short alpha token), then bind the
    # candidate to the nearest plain numeric quantity before the price cells.
    units = [
        token for token in row
        if token["bbox"][0] < limit
        and (token["text"].strip().upper() in UNIT_WORDS
             or UNIT_RE.fullmatch(token["text"].strip()))
    ]
    if not units or not numbers:
        return [], []
    unit = min(
        units,
        key=lambda item: min(abs(item["bbox"][0] - number["bbox"][0]) for number in numbers),
    )
    quantity = min(numbers, key=lambda item: abs(item["bbox"][0] - unit["bbox"][0]))
    return [quantity], [unit]


def _description(row: list[dict[str, Any]], quantity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not quantity:
        return []
    limit = quantity[0]["bbox"][0]
    candidates = [
        token for token in row
        if token["bbox"][2] < limit and re.search(r"[A-Za-z]", token["text"])
        and token["text"].strip().upper() not in UNIT_WORDS
        and not re.fullmatch(r"[A-Za-z]*\d[A-Za-z0-9./_-]*", token["text"].strip())
    ]
    # Marks/containers form a component to the far left.  The rightmost
    # textual component immediately before quantity is the description cell.
    components: list[list[dict[str, Any]]] = []
    for token in sorted(candidates, key=lambda item: (item["bbox"][0], item["bbox"][1], item["index"])):
        if not components or token["bbox"][0] - max(item["bbox"][2] for item in components[-1]) > .04 * quantity[0]["bbox"][0]:
            components.append([token])
        else:
            components[-1].append(token)
    return sorted(components[-1], key=lambda item: (item["bbox"][1], item["bbox"][0], item["index"])) if components else []


def _ci_items(tokens: list[dict[str, Any]], grid: Grid) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for index, row in enumerate(_row_groups(_table_lines(tokens, grid), grid, min_money=2)):
        money = _rightmost_money(row)
        quantity, unit = _quantity_unit(row, money)
        description = _description(row, quantity)
        if not (len(money) == 2 and quantity and unit and description):
            continue
        # Independent structural relation required before an item enters the
        # denominator: description -> quantity/unit -> price -> amount.
        description_x = _box(description)[0]
        quantity_unit_left = min(_box(quantity)[0], _box(unit)[0])
        quantity_unit_right = max(_box(quantity)[2], _box(unit)[2])
        if not (description_x < quantity_unit_left and quantity_unit_right < money[0]["bbox"][0] < money[1]["bbox"][0]):
            continue
        row_fields = [
            _image_evidence(f"items[{index}].description", description, grid, "item_table", "image_table_row_description_quantity_price_amount"),
            _image_evidence(f"items[{index}].quantity", quantity, grid, "item_table", "image_table_row_description_quantity_price_amount"),
            _image_evidence(f"items[{index}].unit", unit, grid, "item_table", "image_table_row_description_quantity_price_amount"),
            _image_evidence(f"items[{index}].unit_price", [money[0]], grid, "item_table", "image_table_row_description_quantity_price_amount"),
            _image_evidence(f"items[{index}].amount", [money[1]], grid, "item_table", "image_table_row_description_quantity_price_amount"),
        ]
        # An item is semantically atomic.  Do not admit a partial row into
        # the denominator when one of its typed source polygons cannot be
        # rendered on the original image; retain all five fields as explicitly
        # ambiguous so independent completeness can still account for the row.
        if any(field["status"] != "available" for field in row_fields):
            row_fields = [
                _ambiguous(field["field_name"], "item_row_has_unrenderable_source_geometry")
                for field in row_fields
            ]
        fields.extend(row_fields)
    return fields


def _pl_items(tokens: list[dict[str, Any]], grid: Grid) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    rows = _table_lines(tokens, grid)
    # A row's unit is frequently printed on a continuation line below the
    # rest of the cells.  First form rows from source-only base lines (text +
    # at least two numeric-looking cells), then bind a compact unit to the
    # nearest plain numeric candidate inside that complete row block.
    def is_base(line: list[dict[str, Any]]) -> bool:
        text = _join(line).upper()
        numeric_like = sum(bool(re.search(r"\d", token["text"])) for token in line)
        has_description_word = any(
            len(re.sub(r"[^A-Za-z]", "", token["text"])) >= 3
            and not re.fullmatch(r"[A-Za-z]*\d[A-Za-z0-9./_-]*", token["text"].strip())
            for token in line
        )
        return numeric_like >= 2 and has_description_word and "TOTAL" not in text

    starts = [position for position, line in enumerate(rows) if is_base(line)]
    grouped_rows = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(rows)
        block = []
        for line in rows[start:end]:
            # Footer totals/signature text is visibly outside the item row;
            # never carry it into the final item merely because it follows
            # the last source row on the page.
            if "TOTAL" in _join(line).upper():
                break
            block.extend(line)
        grouped_rows.append(block)
    for index, row in enumerate(grouped_rows):
        numbers = [token for token in row if re.fullmatch(r"\d+(?:[.,]\d+)?", token["text"].strip())]
        options = []
        for token in row:
            upper = token["text"].strip().upper()
            if not UNIT_RE.fullmatch(token["text"].strip()) or upper in UNIT_STOP_WORDS:
                continue
            left_numbers = [number for number in numbers if number["bbox"][0] <= token["bbox"][0] + .03 * grid.width]
            right_numbers = [number for number in numbers if number["bbox"][0] > token["bbox"][0] + .03 * grid.width]
            if left_numbers and right_numbers:
                quantity = min(left_numbers, key=lambda number: abs(number["bbox"][0] - token["bbox"][0]))
                options.append((abs(quantity["bbox"][0] - token["bbox"][0]), token, quantity))
        if not options:
            continue
        # The merchandise unit belongs to the first typed unit column to the
        # right of the description.  Later KG/PKG cells are net/gross/package
        # logistics values and can be closer to their own numbers, so distance
        # alone would select the wrong semantic column.
        _, unit, quantity = min(options, key=lambda item: (item[1]["bbox"][0], item[0]))
        description = [token for token in row if token["bbox"][2] < quantity["bbox"][0] and re.search(r"[A-Za-z]", token["text"]) and not re.fullmatch(r"[A-Za-z]*\d[A-Za-z0-9./_-]*", token["text"].strip())]
        if not description or not _box(description)[0] < quantity["bbox"][0] < unit["bbox"][0]:
            # Inline or vertically continued quantity/unit pairs share a
            # column, so allow a small normalized column tolerance.
            if not description or not _box(description)[0] < quantity["bbox"][0] or abs(quantity["bbox"][0] - unit["bbox"][0]) > .14 * grid.width:
                continue
        row_fields = [
            _image_evidence(f"items[{index}].description", description, grid, "item_table", "image_table_row_description_quantity_unit"),
            _image_evidence(f"items[{index}].quantity", [quantity], grid, "item_table", "image_table_row_description_quantity_unit"),
            _image_evidence(f"items[{index}].unit", [unit], grid, "item_table", "image_table_row_description_quantity_unit"),
        ]
        if any(field["status"] != "available" for field in row_fields):
            row_fields = [
                _ambiguous(field["field_name"], "item_row_has_unrenderable_source_geometry")
                for field in row_fields
            ]
        fields.extend(row_fields)
    return fields


def _account_for_all_image_rows(fields: list[dict[str, Any]], tokens: list[dict[str, Any]], grid: Grid, doc_type: str) -> list[dict[str, Any]]:
    """Explicitly represent every independently visible item row.

    A typed image/TL row that cannot be mapped without a structural leap is
    not silently omitted.  Its canonical fields remain ``ambiguous_gt`` so
    the denominator is conservative while the completeness audit can prove
    that every source row was considered.
    """
    suffixes = ("description", "quantity", "unit", "unit_price", "amount") if doc_type == "Commercial Invoice" else ("description", "quantity", "unit")
    known = {field["field_name"] for field in fields}
    for index, _ in enumerate(table_row_inventory(tokens, grid, doc_type)):
        row_names = [f"items[{index}].{suffix}" for suffix in suffixes]
        existing = [name for name in row_names if name in known]
        if existing and len(existing) == len(row_names):
            continue
        # A partially inferred row is never allowed.  Remove any partial
        # candidate fields and replace the full canonical row with explicit
        # source ambiguity.
        if existing:
            fields[:] = [field for field in fields if field["field_name"] not in row_names]
            known.difference_update(existing)
        fields.extend(_ambiguous(name, "visible_source_item_row_has_no_complete_typed_semantic_mapping") for name in row_names)
        known.update(row_names)
    return fields


def _preserve_not_applicable(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [field for field in fields if field.get("status") == "not_applicable"]


def build_case(payload: dict[str, Any], doc_type: str, image_path: Path) -> list[dict[str, Any]]:
    """Build a trusted subset; never promote unsupported fields to available."""
    grid = detect_grid(image_path)
    tokens = v3.v2._tokens(payload)
    base = v32.build_v3_2(payload, doc_type)
    fields: list[dict[str, Any]] = _preserve_not_applicable(base)
    parties = _party_fields(doc_type, tokens, grid)
    fields.extend(parties.values())
    if doc_type == "Commercial Invoice":
        fields.extend(_ci_items(tokens, grid))
        fields = _account_for_all_image_rows(fields, tokens, grid, doc_type)
    elif doc_type == "Packing List":
        fields.extend(_pl_items(tokens, grid))
        fields = _account_for_all_image_rows(fields, tokens, grid, doc_type)
    # B/L party blocks are structurally verifiable.  Ports/vessel and table
    # labels remain ambiguous until their printed header can be independently
    # read; no left/right or first-row assumption is promoted as Gold.
    names = {field["field_name"] for field in fields}
    source_row_count = len(table_row_inventory(tokens, grid, doc_type)) if doc_type in {"Commercial Invoice", "Packing List"} else None
    for source in base:
        item_match = re.match(r"items\[(\d+)\]", str(source["field_name"]))
        if item_match and source_row_count is not None and int(item_match.group(1)) >= source_row_count:
            # Do not carry template/example item slots from the previous Gold
            # into a document whose source image has fewer actual rows.
            continue
        if source["field_name"] not in names:
            fields.append(_ambiguous(source["field_name"], "no_image_and_tl_semantic_proof_for_available_value"))
    return fields


def _case_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def build(cases_root: Path, allowlist: Path, old_root: Path, output_root: Path, diff_path: Path) -> dict[str, Any]:
    case_ids = _case_ids(allowlist)
    output_cases = output_root / "cases"
    output_cases.mkdir(parents=True, exist_ok=True)
    changes: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    for case_id in case_ids:
        source = cases_root / case_id
        manifest = json.loads((source / "case_manifest.json").read_text(encoding="utf-8"))
        payload = json.loads((source / "source_annotation.json").read_text(encoding="utf-8"))
        old_fields = json.loads((old_root / case_id / "semantic_gold_fields.json").read_text(encoding="utf-8"))
        fields = build_case(payload, manifest["document_type"], source / "image.png")
        target = output_cases / case_id
        target.mkdir(parents=True, exist_ok=True)
        (target / "case_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "semantic_gold_fields.json").write_text(json.dumps(fields, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        before = {field["field_name"]: field for field in old_fields}
        after = {field["field_name"]: field for field in fields}
        for name in sorted(set(before) | set(after)):
            old, new = before.get(name, {}), after.get(name, {})
            if all(old.get(key) == new.get(key) for key in ("value", "status", "source_token_indices")):
                continue
            changes.append({
                "case_id": case_id, "document_type": manifest["document_type"], "field_name": name,
                "old_value": old.get("value"), "new_value": new.get("value"),
                "old_status": old.get("status"), "new_status": new.get("status"),
                "old_indices": json.dumps(old.get("source_token_indices", [])),
                "new_indices": json.dumps(new.get("source_token_indices", [])),
                "reason": new.get("gold_review"),
            })
        for field in fields:
            counts[f"{manifest['document_type']}:{field['status']}"] += 1
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(changes[0]) if changes else ["case_id", "document_type", "field_name"]
    with diff_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(changes)
    metrics = {"cases": len(case_ids), "changed_fields": len(changes), "status_counts": dict(sorted(counts.items())), "prediction_blind": True, "ocr_read": False, "extractor_read": False, "final_holdout_2_accessed": False}
    (output_root / "gold_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--diff", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.cases_root, args.allowlist, args.old_root, args.output_root, args.diff), ensure_ascii=False))


if __name__ == "__main__":
    main()

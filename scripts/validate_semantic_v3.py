"""Validate semantic-v3 and build a conservative, separate semantic-v3.1.

This module is prediction-blind.  It reads only AI-Hub source annotations,
semantic-v2 audit output, and semantic-v3 candidate gold.  It never reads OCR
or extractor predictions.  semantic-v2 and semantic-v3 files are not changed.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fintra.normalization.values import normalize_date, parse_amount


COUNTRIES = {
    "AUSTRALIA", "BELGIUM", "CANADA", "CHILE", "CHINA", "DENMARK", "EGYPT", "ERITREA",
    "FINLAND", "FRANCE", "GERMANY", "GREECE", "HAITI", "INDIA", "IRELAND", "ISRAEL",
    "ITALY", "JAPAN", "KOREA", "MALAYSIA", "NIGERIA", "NORWAY", "POLAND", "SINGAPORE",
    "SOUTH AFRICA", "SPAIN", "TAIWAN", "THAILAND", "TURKEY", "UNITED STATES", "VIET NAM",
    "VIETNAM",
}
UNITS = {
    "KG", "KGS", "G", "GRAM", "GRAMS", "PC", "PCS", "EA", "EACH", "PKG", "BOX", "CTN",
    "SET", "UNIT", "POUND", "YARD", "DRUM", "BAG", "PIECE", "ST",
}
COMPANY_MARKERS = {
    "CO", "LTD", "INC", "LLC", "CORP", "CORPORATION", "COMPANY", "INDUSTRIES", "ENTERPRISES",
    "TRADING", "SYSTEMS", "STRUCTURES", "TECHNOLOGIES", "SOLUTIONS", "GROUP", "OFFICE",
}
TRANSPORT_TERMS = {"FOB", "CIF", "CFR", "DAF", "DDP", "DDU", "CFS", "CY", "DEQ"}


def _base(field_name: str) -> str:
    return re.sub(r"^items\[\d+\]\.", "", field_name)


def _norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(text).upper()).strip()


def _is_country_only(text: str) -> bool:
    return _norm(text) in {_norm(country) for country in COUNTRIES}


def _is_phone(text: str) -> bool:
    return bool(re.search(r"(?:TEL|FAX|\+?\d)[^A-Za-z]{0,5}\d", text.upper())) and len(re.findall(r"\d", text)) >= 5


def _is_address_only(text: str) -> bool:
    upper = text.upper()
    has_address = bool(re.search(r"\b(?:STREET|ROAD|AVENUE|CITY|DISTRICT|KOREA|JAPAN|CHINA|TAIWAN|USA|UNITED STATES|QLD|AK|REP\.)\b", upper)) or bool(re.search(r"(?:^|[\s,])(?:ST|RD|AVE)\.?(?:[\s,]|$)", upper)) or bool(re.search(r"\b\d{4,6}\b", text))
    words = set(re.findall(r"[A-Z][A-Z.'-]*", upper))
    return has_address and not words.intersection(COMPANY_MARKERS)


def _party_valid(text: str) -> tuple[bool, str]:
    upper = text.upper().strip()
    if not upper:
        return False, "empty_party_value"
    if _is_phone(upper):
        return False, "party_is_phone_or_fax"
    if "@" in upper:
        return False, "party_is_email"
    if _is_country_only(upper):
        return False, "party_is_country_only"
    if _is_address_only(upper):
        return False, "party_is_address_only"
    if re.search(r"\bV\s*\.?\s*\d+\b", upper):
        return False, "party_contains_voyage_expression"
    words = set(re.findall(r"[A-Z][A-Z.'-]*", upper))
    if words.intersection(TRANSPORT_TERMS):
        return False, "party_contains_heading_or_transport_term"
    # A place/country line is not an organisation merely because it has two
    # or more words (for example, "REP OF SINGAPORE").  Keep this rule
    # prediction-blind: it uses only lexical type evidence from the gold text.
    if any(re.search(r"\b" + re.escape(country) + r"\b", upper) for country in COUNTRIES) and not words.intersection(COMPANY_MARKERS):
        return False, "party_is_country_or_place_text"
    if "," in upper and any(re.search(r"\b" + re.escape(country) + r"\b", upper) for country in COUNTRIES) and not words.intersection(COMPANY_MARKERS):
        return False, "party_is_port_or_place_text"
    if len(words) < 2:
        return False, "party_not_organization_like"
    return True, ""


def _vessel_valid(text: str) -> tuple[bool, str]:
    upper = text.upper().strip()
    words = re.findall(r"[A-Z][A-Z.'-]*", upper)
    if not words:
        return False, "empty_vessel_value"
    if words[0] in TRANSPORT_TERMS:
        return False, "vessel_starts_with_transport_or_incoterm"
    if _is_country_only(upper) or _is_phone(upper) or _is_address_only(upper):
        return False, "vessel_is_address_country_or_phone"
    if "," in upper and any(re.search(r"\b" + re.escape(country) + r"\b", upper) for country in COUNTRIES):
        return False, "vessel_is_port_or_place_text"
    return True, ""


def _port_valid(text: str) -> tuple[bool, str]:
    upper = text.upper().strip()
    if not upper or _is_phone(upper) or _is_country_only(upper):
        return False, "port_is_empty_phone_or_country_only"
    if re.match(r"^(?:FOB|CIF|CFR|DAF|DDP|DDU|CFS|CY|DEQ)\b", upper):
        return False, "port_starts_with_transport_term"
    # A normal port candidate is intentionally a place string such as
    # ``YOKOHAMA, JAPAN``; the generic address detector must not reject it.
    if _is_address_only(upper) and "," not in upper:
        return False, "port_is_address_text"
    if "," not in upper:
        return False, "port_lacks_city_country_separator"
    if upper.endswith(",") or upper.count(",") != 1:
        return False, "port_has_multiple_or_trailing_place_segments"
    if not re.search(r"[A-Z]", upper):
        return False, "port_has_no_alphabetic_place_text"
    return True, ""


def _numeric(text: str) -> bool:
    return bool(re.fullmatch(r"\s*[+$€£¥₩]?\s*\d[\d,]*(?:\.\d+)?\s*[-+]?\s*", text))


def _description_valid(text: str, peers: list[str]) -> tuple[bool, str]:
    stripped = text.strip()
    if not re.search(r"[A-Za-z]", stripped):
        return False, "description_has_no_alphabetic_word"
    # Mixed product text and numbers (e.g. ``PUMP 3166.31``) is still a
    # textual description.  Only a value that is wholly numeric/currency or
    # a wholly parseable date is rejected here.
    if _numeric(stripped) or normalize_date(stripped) is not None:
        return False, "description_is_numeric_currency_amount_or_date"
    normalized = _norm(stripped)
    if any(normalized and normalized == _norm(peer) for peer in peers if peer):
        return False, "description_equals_same_row_numeric_field"
    return True, ""


def _field_valid(field: dict[str, Any], row_peers: list[str], document_type: str) -> tuple[bool, str]:
    value = str(field.get("value") or "")
    base = _base(field["field_name"])
    if base == "description":
        return _description_valid(value, row_peers)
    if base == "quantity":
        return (_numeric(value), "" if _numeric(value) else "quantity_is_not_numeric_only")
    if base in {"unit", "weight_unit"}:
        good = bool(re.fullmatch(r"[A-Za-z]+", value.strip())) and (_norm(value) in UNITS or bool(re.fullmatch(r"[A-Za-z]+", value.strip())))
        return good, "" if good else "unit_is_not_explicit_or_alphabetic"
    if base in {"unit_price", "amount", "total_amount", "gross_weight", "net_weight", "package_count"}:
        good = _numeric(value) or parse_amount(value) is not None
        return good, "" if good else "numeric_field_is_not_currency_or_numeric_compatible"
    if base in {"seller", "buyer", "exporter", "consignee", "shipper", "notify_party"}:
        return _party_valid(value)
    if base == "vessel":
        return _vessel_valid(value)
    if base in {"port_of_loading", "port_of_discharge"}:
        return _port_valid(value)
    if base in {"invoice_date", "date", "shipment_date", "on_board_date"}:
        good = normalize_date(value) is not None
        return good, "" if good else "date_is_not_parseable"
    return True, ""


def _tokens(gt: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result = {}
    for index, item in enumerate(gt.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) < 3 or len(xs) != len(ys):
            continue
        result[index] = {"text": str(item.get("data") or ""), "bbox": [min(xs), min(ys), max(xs), max(ys)]}
    return result


def _x_position(field: dict[str, Any], token_map: dict[int, dict[str, Any]]) -> float | None:
    selected = [token_map[index] for index in field.get("source_token_indices", []) if index in token_map]
    if not selected:
        return None
    return min(item["bbox"][0] for item in selected)


def _row_peers(field: dict[str, Any], gold_fields: list[dict[str, Any]]) -> list[str]:
    match = re.match(r"items\[(\d+)\]\.description$", field["field_name"])
    if not match:
        return []
    index = match.group(1)
    return [str(other.get("value") or "") for other in gold_fields if re.match(rf"items\[{index}\]\.(?:quantity|unit|unit_price|amount)$", other["field_name"]) and other.get("status") == "available"]


def _order_reason(gold_fields: list[dict[str, Any]], token_map: dict[int, dict[str, Any]]) -> list[tuple[str, str]]:
    violations = []
    by_row: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for field in gold_fields:
        match = re.match(r"items\[(\d+)\]\.(description|quantity|unit|unit_price|amount)$", field["field_name"])
        if match and field.get("status") == "available":
            by_row[match.group(1)][match.group(2)] = field
    order = ("description", "quantity", "unit", "unit_price", "amount")
    for row, fields in by_row.items():
        positions = [(name, _x_position(fields[name], token_map)) for name in order if name in fields and _x_position(fields[name], token_map) is not None]
        for (left_name, left_x), (right_name, right_x) in zip(positions, positions[1:]):
            # Quantity and unit are a logical pair and may share one source
            # column/token (``7 PC``).  All other transitions must move right.
            same_quantity_unit_column = {left_name, right_name} == {"quantity", "unit"}
            if left_x > right_x or (left_x == right_x and not same_quantity_unit_column):
                violations.append((f"items[{row}].{right_name}", f"table_column_order_violation:{left_name}>={right_name}"))
    return violations


def validate_v3(cases_root: Path, v3_root: Path, v2_audit_csv: Path, output_dir: Path) -> dict[str, Any]:
    v2_valid: dict[tuple[str, str], bool] = {}
    with v2_audit_csv.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            v2_valid[(row["case_id"], row["field_name"])] = row["classification"] == "VALID_GOLD"
    invalid_rows: list[dict[str, Any]] = []
    v31_fields_by_case: dict[str, list[dict[str, Any]]] = {}
    changes: list[dict[str, Any]] = []
    fallback_counts = Counter()
    source_status_counts = Counter()
    for source_case in sorted(path for path in cases_root.iterdir() if path.is_dir()):
        manifest_path, gt_path = source_case / "case_manifest.json", source_case / "gt.json"
        v3_path = v3_root / source_case.name / "semantic_gold_fields.json"
        v2_path = source_case / "semantic_gold_fields.json"
        if not all(path.is_file() for path in (manifest_path, gt_path, v2_path, v3_path)):
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        token_map = _tokens(json.loads(gt_path.read_text(encoding="utf-8")))
        v2_fields = json.loads(v2_path.read_text(encoding="utf-8"))
        v3_fields = json.loads(v3_path.read_text(encoding="utf-8"))
        v2_by_name = {field["field_name"]: field for field in v2_fields}
        order_violations = dict(_order_reason(v3_fields, token_map))
        output_fields: list[dict[str, Any]] = []
        for field in v3_fields:
            candidate = deepcopy(field)
            source_status_counts[field.get("status", "unknown")] += 1
            if field.get("status") == "available":
                peers = _row_peers(field, v3_fields)
                good, reason = _field_valid(field, peers, manifest["document_type"])
                if field["field_name"] in order_violations:
                    good = False
                    reason = ";".join(filter(None, [reason, order_violations[field["field_name"]]]))
                if not good:
                    invalid_rows.append({
                        "case_id": manifest["case_id"], "document_type": manifest["document_type"],
                        "field_name": field["field_name"], "current_value": field.get("value"),
                        "invariant_failed": reason, "source_token_indices": json.dumps(field.get("source_token_indices", [])),
                        "reason": "semantic-v3 candidate rejected by prediction-blind invariant validation",
                    })
                    old = v2_by_name.get(field["field_name"], {})
                    if old.get("status") == "available" and v2_valid.get((manifest["case_id"], field["field_name"]), False):
                        candidate = deepcopy(old)
                        candidate["gold_review"] = "semantic-v2-valid-fallback_after_v3_invariant_failure"
                        fallback_counts["v2_valid_fallback"] += 1
                    else:
                        candidate = {"field_name": field["field_name"], "value": None, "status": "ambiguous_gt", "source_text": None, "bbox": None, "source_token_indices": [], "gold_review": "v3_invalid_and_v2_not_valid_or_not_available"}
                        fallback_counts["ambiguous_after_rejection"] += 1
                else:
                    fallback_counts["v3_kept"] += 1
            elif field.get("status") == "ambiguous_gt":
                old = v2_by_name.get(field["field_name"], {})
                if old.get("status") == "available" and v2_valid.get((manifest["case_id"], field["field_name"]), False):
                    candidate = deepcopy(old)
                    candidate["gold_review"] = "semantic-v2-valid-fallback_for_unresolved_v3_candidate"
                    fallback_counts["v2_valid_fallback"] += 1
                else:
                    fallback_counts["ambiguous_retained"] += 1
            output_fields.append(candidate)
        # A v2 fallback is acceptable only if it also satisfies the strict
        # v3.1 type invariants.  If it does not, retaining it would violate
        # the promised zero-invalid invariant count; ambiguity is safer than
        # silently accepting a structurally invalid fallback.
        post_invalid = dict(_order_reason(output_fields, token_map))
        for candidate in output_fields:
            if candidate.get("status") != "available":
                continue
            field_name = candidate["field_name"]
            good, reason = _field_valid(candidate, _row_peers(candidate, output_fields), manifest["document_type"])
            if field_name in post_invalid:
                good = False
                reason = ";".join(filter(None, [reason, post_invalid[field_name]]))
            if not good:
                old_candidate = deepcopy(candidate)
                candidate.update({"value": None, "status": "ambiguous_gt", "source_text": None, "bbox": None, "source_token_indices": [], "gold_review": "selected_fallback_failed_strict_v3_1_validation"})
                changes.append({
                    "case_id": manifest["case_id"], "document_type": manifest["document_type"], "field_name": field_name,
                    "v3_gold": next((f.get("value") for f in v3_fields if f["field_name"] == field_name), None),
                    "v3_1_gold": None, "v3_status": next((f.get("status") for f in v3_fields if f["field_name"] == field_name), None),
                    "v3_1_status": "ambiguous_gt", "change_reason": f"{candidate['gold_review']}:{reason}",
                    "v3_source_token_indices": json.dumps(next((f.get("source_token_indices", []) for f in v3_fields if f["field_name"] == field_name), [])),
                    "v3_1_source_token_indices": "[]", "source_token_indices_changed": bool(old_candidate.get("source_token_indices")),
                })
        # Emit one diff row per changed field after the final v3.1 decision.
        changes = [row for row in changes if not (row["case_id"] == manifest["case_id"] and row["field_name"] in {f["field_name"] for f in v3_fields})]
        for original, candidate in zip(v3_fields, output_fields):
            if (original.get("value"), original.get("status"), original.get("source_token_indices", [])) != (candidate.get("value"), candidate.get("status"), candidate.get("source_token_indices", [])):
                changes.append({
                    "case_id": manifest["case_id"], "document_type": manifest["document_type"], "field_name": original["field_name"],
                    "v3_gold": original.get("value"), "v3_1_gold": candidate.get("value"),
                    "v3_status": original.get("status"), "v3_1_status": candidate.get("status"),
                    "change_reason": candidate.get("gold_review", "semantic-v3.1 rule"),
                    "v3_source_token_indices": json.dumps(original.get("source_token_indices", [])),
                    "v3_1_source_token_indices": json.dumps(candidate.get("source_token_indices", [])),
                    "source_token_indices_changed": original.get("source_token_indices", []) != candidate.get("source_token_indices", []),
                })
        target = output_dir / "cases" / source_case.name
        target.mkdir(parents=True, exist_ok=True)
        (target / "case_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "semantic_gold_fields.json").write_text(json.dumps(output_fields, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        v31_fields_by_case[source_case.name] = output_fields
    output_dir.mkdir(parents=True, exist_ok=True)
    invalid_fields = ["case_id", "document_type", "field_name", "current_value", "invariant_failed", "source_token_indices", "reason"]
    with (output_dir / "v3_invalid_gold.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=invalid_fields)
        writer.writeheader()
        writer.writerows(invalid_rows)
    diff_fields = list(changes[0]) if changes else ["case_id", "document_type", "field_name", "v3_gold", "v3_1_gold", "change_reason"]
    with (output_dir / "v3_to_v3_1_diff.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=diff_fields)
        writer.writeheader()
        writer.writerows(changes)
    residual_invalid = []
    for fields in v31_fields_by_case.values():
        for field in fields:
            if field.get("status") == "available":
                good, reason = _field_valid(field, _row_peers(field, fields), "")
                if not good:
                    residual_invalid.append((field["field_name"], reason))
    by_type = Counter(row["document_type"] for row in invalid_rows)
    by_field = Counter(row["field_name"] for row in invalid_rows)
    metrics = {
        "prediction_blind": True,
        "v3_candidate_available": sum(value == "available" for value in source_status_counts.elements()),
        "v3_invalid_fields": len(invalid_rows),
        "v3_to_v3_1_changed_fields": len(changes),
        "v3_1_residual_invariant_violations": len(residual_invalid),
        "v3_1_invariant_status": "PASS" if not residual_invalid else "FAIL",
        "invalid_by_document_type": dict(sorted(by_type.items())),
        "invalid_by_field": dict(sorted(by_field.items())),
        "v3_1_decisions": dict(fallback_counts),
        "v3_source_status_counts": dict(source_status_counts),
    }
    (output_dir / "v3_1_validation_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("artifacts/fintra/field_eval/cases"))
    parser.add_argument("--v3-root", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v3/cases"))
    parser.add_argument("--v2-audit", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v2/suspect_gold.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/gold_audit/semantic-v3.1"))
    args = parser.parse_args()
    print(json.dumps(validate_v3(args.cases, args.v3_root, args.v2_audit, args.output_dir), ensure_ascii=False))


if __name__ == "__main__":
    main()

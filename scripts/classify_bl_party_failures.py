"""Classify frozen B/L party failures without changing gold or OCR output.

The classification uses only semantic-gold token geometry, frozen Paddle OCR
regions, and the active extractor CSV.  Predictions are used to identify an
extractor failure, never to create or alter gold.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.extraction.documents import (
    _PARTY_COUNTRY_LINES,
    _canonical,
    _is_party_value_candidate,
    _line_groups,
    _party_heading_role,
)
from fintra.ocr.adapter import OCRResult
from scripts.evaluate_field_extraction import normalize_field
from scripts.evaluate_ocr_stages import RECOVERABLE, _candidate_regions, _field_evidence, _read_ocr

PARTY_FIELDS = {"shipper", "consignee", "notify_party"}
SAME_AS = re.compile(r"^SAME\s+AS\s+(?:THE\s+)?(?:CONSIGNEE|SHIPPER|BUYER|EXPORTER|SELLER)$", re.I)
PARTY_COUNTRIES = _PARTY_COUNTRY_LINES | {
    "NEW ZEALAND", "UNITED KINGDOM", "NETHERLANDS", "BELGIUM", "PORTUGAL",
    "IRELAND", "CHILE", "SAUDI ARABIA", "SOUTH KOREA", "HONG KONG",
}


def _load_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}


def _box(item: dict) -> tuple[float, float, float, float]:
    xs, ys = item["x"], item["y"]
    return min(xs), min(ys), max(xs), max(ys)


def _gold_tokens(case_path: Path, field: dict) -> list[dict]:
    raw = json.loads((case_path / "gt.json").read_text(encoding="utf-8"))
    return [{"polygon": list(zip(raw["bbox"][i]["x"], raw["bbox"][i]["y"]))}
            for i in field.get("source_token_indices", [])]


def _anchor_roles(result: OCRResult) -> list[tuple[float, str]]:
    pool = [region for region in result.regions
            if region.bbox[0] <= 800 and 100 <= region.bbox[1] <= 900]
    anchors = []
    for line in _line_groups(pool):
        role = _party_heading_role(" ".join(region.text for region in line))
        if role:
            anchors.append((min(region.bbox[1] for region in line), role))
    return sorted(anchors)


def _candidate_role(y: float, anchors: list[tuple[float, str]]) -> str | None:
    if not anchors:
        return None
    if y < anchors[0][0]:
        return "shipper" if anchors[0][1] != "shipper" else None
    index = max(i for i, (anchor_y, _) in enumerate(anchors) if y >= anchor_y)
    if anchors[0][1] == "shipper":
        return ("shipper", "consignee", "notify_party")[min(index, 2)]
    if anchors[0][1] == "consignee" and not any(role == "shipper" for _, role in anchors):
        return ("consignee", "notify_party")[min(index, 1)]
    return anchors[index][1]


def _candidate_role_for_gold(result: OCRResult, expected: str, field: str) -> tuple[str | None, str]:
    anchors = _anchor_roles(result)
    pool = [region for region in result.regions
            if region.bbox[0] <= 800 and 100 <= region.bbox[1] <= 900]
    target = normalize_field(expected, field) or ""
    best = None
    for line in _line_groups(pool):
        text = " ".join(region.text.strip() for region in line if region.text.strip()).strip()
        if not text:
            continue
        observed = normalize_field(text, field) or ""
        score = SequenceMatcher(None, target.casefold(), observed.casefold()).ratio()
        if observed == target or score >= 0.90:
            y = min(region.bbox[1] for region in line)
            if best is None or score > best[0]:
                best = (score, y, text)
    if best is None:
        return None, "gold token has no matching OCR party line"
    role = _candidate_role(best[1], anchors)
    if role and role != field:
        return role, f"gold value is located in {role} block, not {field} block"
    return role, "gold value is in the expected party block"


def _gold_type_problem(value: str) -> str | None:
    if SAME_AS.fullmatch(value.strip()):
        return None
    upper = value.upper().strip()
    if _canonical(upper) in PARTY_COUNTRIES:
        return "party gold is country-only"
    if re.search(r"\bV\s*\.?\s*\d+\b", upper):
        return "party gold is a voyage expression"
    if re.search(r"\b(?:TEL|FAX|PHONE|EMAIL|ADDRESS|ROAD|STREET|AVENUE|DISTRICT)\b", upper):
        return "party gold is contact/address text"
    if not _is_party_value_candidate(value):
        return "party gold fails typed party candidate validation"
    return None


def classify(args: argparse.Namespace) -> list[dict[str, str]]:
    predictions = _load_rows(args.field_results)
    rows: list[dict[str, str]] = []
    for case_path in sorted(path for path in args.cases.iterdir() if path.is_dir()):
        manifest_path = case_path / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("document_type") != "B/L":
            continue
        case_id = manifest["case_id"]
        gold = json.loads((args.gold_root / case_id / "semantic_gold_fields.json").read_text(encoding="utf-8"))
        ocr_path = case_path / "outputs" / "recognition" / "paddle.json"
        result = OCRResult.from_json(ocr_path, document_type="B/L", preserve_raw=False)
        ocr_regions = _read_ocr(ocr_path)
        case = {"path": case_path, "case_id": case_id, "document_id": manifest.get("document_id", case_id), "document_type": "B/L"}
        evidence_rows = {(item["field_name"]): item for item in _field_evidence(case, "paddle", ocr_regions, args.gold_root)}
        for field in gold:
            name = field["field_name"]
            if name not in PARTY_FIELDS or field.get("status") != "available":
                continue
            prediction = predictions.get((case_id, name), {})
            if prediction.get("status") in {"exact_match", "normalized_match"}:
                continue
            expected = str(field.get("value") or "")
            evidence = evidence_rows.get(name, {})
            stage = evidence.get("classification", "OCR_DETECTION_MISSING")
            classification = "OCR_MISSING"
            reason = f"raw OCR classification={stage}"
            if stage in RECOVERABLE:
                type_problem = _gold_type_problem(expected)
                role, role_reason = _candidate_role_for_gold(result, expected, name)
                if type_problem:
                    classification = "GOLD_AMBIGUOUS_OR_MISMATCH"
                    reason = type_problem
                elif role and role != name:
                    classification = "GOLD_AMBIGUOUS_OR_MISMATCH"
                    reason = role_reason
                else:
                    classification = "EXTRACTOR_WRONG"
                    reason = "recoverable party evidence exists in the expected block but active selection is not correct"
            group_match = re.match(r"(bl\d\d)", case_id, re.I)
            rows.append({
                "case_id": case_id,
                "source_group": group_match.group(1).upper() if group_match else "UNKNOWN",
                "document_type": "B/L",
                "field_name": name,
                "gt_value": expected,
                "predicted_value": prediction.get("predicted_value", ""),
                "extractor_source_text": prediction.get("source_text", ""),
                "ocr_classification": stage,
                "classification": classification,
                "reason": reason,
                "ocr_closest_text": evidence.get("closest_ocr_text", ""),
                "ocr_neighboring_texts": evidence.get("neighboring_ocr_texts", ""),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--field-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = classify(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "bl_party_failure_classification.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["case_id"])
        writer.writeheader(); writer.writerows(rows)
    by_field = defaultdict(Counter)
    by_group = defaultdict(Counter)
    for row in rows:
        by_field[row["field_name"]][row["classification"]] += 1
        by_group[row["source_group"]][row["classification"]] += 1
    metrics = {"rows": len(rows), "by_field": {key: dict(value) for key, value in sorted(by_field.items())}, "by_source_group": {key: dict(value) for key, value in sorted(by_group.items())}, "output": str(csv_path)}
    (args.output_dir / "bl_party_failure_classification.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()

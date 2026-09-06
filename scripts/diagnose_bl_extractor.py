"""Diagnose B/L field failures without changing frozen OCR or semantic gold.

This report deliberately separates OCR evidence availability from extractor
selection.  It is an analysis artifact generator; it does not feed gold or
predictions back into the extractor.
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
    _PARTY_COMPANY_MARKERS,
    _PARTY_COUNTRY_LINES,
    _canonical,
    _is_party_value_candidate,
    _line_groups,
    _regions,
)
from fintra.ocr.adapter import OCRResult
from scripts.evaluate_field_extraction import normalize_field


PARTY_FIELDS = {"shipper", "consignee", "notify_party"}
BL_FIELDS = (
    "bl_number", "shipper", "consignee", "notify_party", "vessel",
    "port_of_loading", "port_of_discharge", "shipment_date", "package_count",
    "gross_weight", "weight_unit", "goods_description",
)


def _load_csv(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}


def _bbox_text(value: str) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    try:
        polygon = json.loads(value)
        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        return min(xs), min(ys), max(xs), max(ys)
    except (TypeError, ValueError, json.JSONDecodeError, IndexError):
        return None


def _line_text(line: list) -> str:
    return " ".join(region.text.strip() for region in line if region.text.strip()).strip()


def _party_candidates(result: OCRResult) -> list[dict[str, object]]:
    # The pool is intentionally broad enough to expose scope failures.  The
    # report does not use this pool to produce application predictions.
    pool = [region for region in _regions(result)
            if region.bbox[0] <= 800 and 170 <= region.bbox[1] <= 850]
    candidates = []
    for line in _line_groups(pool):
        text = _line_text(line)
        if not text:
            continue
        value = text
        # Keep the same structural cleanup used by the active resolver only
        # for diagnostics, so contamination can be classified separately.
        if _is_party_value_candidate(value):
            candidates.append({
                "text": value,
                "bbox": [min(r.bbox[0] for r in line), min(r.bbox[1] for r in line),
                         max(r.bbox[2] for r in line), max(r.bbox[3] for r in line)],
                "region_indices": [r.index for r in line],
            })
    return candidates


def _match_score(gt: str, candidate: str) -> float:
    return SequenceMatcher(None, normalize_field(gt, "shipper") or "", normalize_field(candidate, "shipper") or "").ratio()


def _classification(selected: dict[str, str], gt_candidate: dict[str, object] | None, field: str) -> str:
    value = selected.get("predicted_value", "")
    source = selected.get("source_text", "")
    if not value:
        return "candidate_generation_miss" if gt_candidate is None else "wrong_candidate_ranking"
    upper = value.upper()
    if re.search(r"\b(?:SHIPPER|CONSIGNEE|NOTIFY|PARTY|EXPORTER|SELLER|BUYER)\b", upper):
        return "heading_contamination"
    if re.search(r"\b(?:TEL|FAX|PHONE|EMAIL|ADDRESS|ROOM|ROAD|STREET|AVENUE|DISTRICT)\b", upper) or _canonical(value) in _PARTY_COUNTRY_LINES:
        return "address_country_selected"
    if re.search(r"\b(?:VESSEL|VOY|PORT|FOB|CIF|CFR|DAF|CFS|CY|DDP|DDU|DEQ)\b|\bV\.?\s*\d+\b", upper):
        return "notice_text_selected"
    selected_box = _bbox_text(selected.get("bbox", ""))
    if selected_box and selected_box[0] > 800:
        return "wrong_column_scope"
    return "wrong_candidate_ranking" if gt_candidate is not None else "wrong_block_boundary"


def build(args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    predictions = _load_csv(args.field_results)
    recoverable = _load_csv(args.recoverable_csv)
    matrix_rows = []
    diagnostics = []
    for case_dir in sorted(path for path in args.cases.iterdir() if path.is_dir()):
        manifest_path = case_dir / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("document_type") != "B/L":
            continue
        case_id = manifest["case_id"]
        gold = json.loads((args.gold_root / case_id / "semantic_gold_fields.json").read_text(encoding="utf-8"))
        result = OCRResult.from_json(case_dir / "outputs" / "recognition" / "paddle.json", document_type="B/L", preserve_raw=False)
        candidates = _party_candidates(result)
        for item in gold:
            field = item["field_name"]
            if field not in BL_FIELDS:
                continue
            row = predictions.get((case_id, field), {})
            evidence = recoverable.get((case_id, field), {})
            applicable = item.get("status") == "available"
            matrix_rows.append({
                "case_id": case_id, "document_type": "B/L", "field_name": field,
                "applicable": str(applicable),
                "correct": str(row.get("status") in {"exact_match", "normalized_match"}),
                "wrong": str(row.get("status") == "wrong"),
                "missing": str(row.get("status") == "missing"),
                "raw_ocr_recoverable": str(bool(evidence)),
                "ocr_unrecoverable": str(applicable and not evidence),
                "predicted_value": row.get("predicted_value", ""),
                "gt_value": item.get("value", ""),
                "extractor_evidence_text": row.get("source_text", ""),
            })
            if field not in PARTY_FIELDS or not evidence or row.get("status") in {"exact_match", "normalized_match"}:
                continue
            gt = str(item.get("value") or "")
            scored = sorted((( _match_score(gt, str(c["text"])), c) for c in candidates), reverse=True, key=lambda pair: pair[0])
            gt_candidate = next((c for score, c in scored if normalize_field(gt, field) == normalize_field(str(c["text"]), field)), None)
            gt_rank = next((index for index, (score, c) in enumerate(scored, 1) if c is gt_candidate), "")
            diagnostics.append({
                "case_id": case_id, "field_name": field,
                "raw_ocr_recoverable": "true",
                "gt_candidate_generated": str(gt_candidate is not None).lower(),
                "gt_candidate_rank": gt_rank,
                "selected_candidate": row.get("predicted_value", ""),
                "classification": _classification(row, gt_candidate, field),
                "gt_value": gt,
                "candidate_texts": " || ".join(str(c["text"]) for _, c in scored[:10]),
                "candidate_scores": " || ".join(f"{score:.3f}" for score, _ in scored[:10]),
                "extractor_evidence_text": row.get("source_text", ""),
                "ocr_evidence_text": evidence.get("combined_ocr_text", ""),
            })
    return matrix_rows, diagnostics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--field-results", type=Path, required=True)
    parser.add_argument("--recoverable-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    matrix, diagnostics = build(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = args.output_dir / "bl_failure_matrix.csv"
    diagnostic_path = args.output_dir / "bl_party_diagnostics.csv"
    for path, rows in ((matrix_path, matrix), (diagnostic_path, diagnostics)):
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["case_id"])
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({"matrix": str(matrix_path), "party_diagnostics": str(diagnostic_path),
                      "matrix_rows": len(matrix), "party_failures": len(diagnostics),
                      "classification": Counter(row["classification"] for row in diagnostics)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

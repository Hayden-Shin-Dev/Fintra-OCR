"""Audit a generated Fintra Gold candidate against the original Training TL.

This is deliberately prediction-blind: it reads only the original TL JSON,
the case manifest/source copy, and the candidate Gold.  Raw TL is word-level
and has no semantic field labels, so semantic-role verification is reported
explicitly as unprovable unless a structural invariant is decisive.
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


NUMERIC = re.compile(r"^[+$-]?\s*\d[\d,./() +:-]*(?:[A-Za-z]+)?$")
DATE = re.compile(
    r"\d{1,4}[-/]?[A-Za-z]{3,9}[-/]?\d{1,4}|"
    r"[A-Za-z]{3,9}\s+\d{1,2}[, ]+\d{4}|"
    r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}", re.I
)
WIDTH = 1654.0


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    return {
        str(item["stable_sample_id"]): item
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
        for item in [json.loads(line)]
    }


def find_tl_dir(training_root: Path) -> Path:
    candidates = [p for p in training_root.iterdir() if p.is_dir() and any(p.glob("TL*.zip"))]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one TL directory, found {candidates}")
    return candidates[0]


def load_tl(tl_dir: Path, row: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    source_group = str(row["source_group"])
    archives = list(tl_dir.glob(f"TL*{source_group}.zip"))
    if len(archives) != 1:
        raise RuntimeError(f"expected one TL archive for {source_group}, found {archives}")
    with zipfile.ZipFile(archives[0]) as handle:
        requested = str(row["label_entry"])
        names = [requested, requested.lstrip("/")]
        name = next((candidate for candidate in names if candidate in handle.namelist()), None)
        if name is None:
            raise KeyError(f"no TL entry for {requested!r} in {archives[0]}")
        payload = json.loads(handle.read(name).decode("utf-8-sig"))
    return payload, archives[0]


def raw_tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
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


def canonical_token_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"data": item.get("data"), "x": item.get("x"), "y": item.get("y")}
            for item in payload.get("bbox", [])]


def bbox_union(indices: list[int], tokens: list[dict[str, Any]]) -> list[float] | None:
    selected = [token["bbox"] for token in tokens if token["index"] in set(indices)]
    if not selected:
        return None
    return [min(box[0] for box in selected), min(box[1] for box in selected),
            max(box[2] for box in selected), max(box[3] for box in selected)]


def flatten_bbox(value: Any) -> list[float] | None:
    if not isinstance(value, list):
        return None
    if len(value) == 4 and all(isinstance(x, (int, float)) for x in value):
        return [float(x) for x in value]
    points = [point for point in value if isinstance(point, list) and len(point) >= 2]
    if not points:
        return None
    return [float(min(point[0] for point in points)), float(min(point[1] for point in points)),
            float(max(point[0] for point in points)), float(max(point[1] for point in points))]


def same_bbox(left: list[float] | None, right: list[float] | None) -> bool:
    return left is not None and right is not None and all(abs(a - b) < 1e-6 for a, b in zip(left, right))


def reading_order_text(selected: list[dict[str, Any]]) -> str:
    """Read selected TL words by geometry, keeping near-y words on one line."""
    lines: list[dict[str, Any]] = []
    for token in sorted(selected, key=lambda item: ((item["bbox"][1] + item["bbox"][3]) / 2, item["bbox"][0])):
        center_y = (token["bbox"][1] + token["bbox"][3]) / 2
        line = next((candidate for candidate in lines if abs(candidate["center_y"] - center_y) <= 18), None)
        if line is None:
            line = {"center_y": center_y, "tokens": []}
            lines.append(line)
        line["tokens"].append(token)
        line["center_y"] = sum((item["bbox"][1] + item["bbox"][3]) / 2 for item in line["tokens"]) / len(line["tokens"])
    return " ".join(token["text"] for line in sorted(lines, key=lambda item: item["center_y"])
                   for token in sorted(line["tokens"], key=lambda item: item["bbox"][0]))


def field_type_issue(name: str, value: str) -> str | None:
    leaf = name.rsplit(".", 1)[-1]
    if leaf.endswith("description") or leaf == "goods_description":
        if not re.search(r"[A-Za-z]", value) or NUMERIC.fullmatch(value):
            return "description_type"
    elif leaf.endswith("quantity") or leaf.endswith("unit_price") or leaf.endswith("amount") \
            or leaf in {"total_amount", "gross_weight", "net_weight", "package_count"}:
        if not NUMERIC.fullmatch(value):
            return "numeric_type"
    elif leaf.endswith("unit"):
        if not re.fullmatch(r"[A-Za-z]+", value):
            return "unit_type"
    elif "date" in leaf or leaf == "date":
        if not DATE.search(value):
            return "date_type"
    if leaf in {"port_of_loading", "port_of_discharge"} and "," not in value:
        return "port_place_shape"
    return None


def item_row_audit(fields: list[dict[str, Any]], tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for field in fields:
        match = re.match(r"items\[(\d+)\]\.(description|quantity|unit|unit_price|amount)$", str(field["field_name"]))
        if not match or field.get("status") != "available":
            continue
        grouped[int(match.group(1))][match.group(2)] = field
    issues = []
    for row_index, row in grouped.items():
        centers = {}
        for role, field in row.items():
            box = bbox_union([int(x) for x in field.get("source_token_indices", [])], tokens)
            if box:
                centers[role] = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        present = [role for role in ("description", "quantity", "unit", "unit_price", "amount") if role in centers]
        if len(present) >= 2:
            y_values = [centers[role][1] for role in present]
            if max(y_values) - min(y_values) > 55:
                issues.append({"row": row_index, "invariant": "row_alignment", "reason": "available item fields are not on one row"})
            x_values = [centers[role][0] for role in present]
            # Quantity and unit may be stacked in the same source column;
            # tolerate small center jitter for that pair.
            if any(x_values[i] > x_values[i + 1] + 10.0 for i in range(len(x_values) - 1)):
                issues.append({"row": row_index, "invariant": "column_order", "reason": "item columns are not left-to-right description/quantity/unit/unit_price/amount"})
    return issues


def audit_case(case_id: str, manifest_row: dict[str, Any], cases_root: Path, gold_root: Path, tl_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_payload, archive = load_tl(tl_dir, manifest_row)
    raw = raw_tokens(raw_payload)
    source_path = cases_root / case_id / "source_annotation.json"
    candidate_path = gold_root / case_id / "semantic_gold_fields.json"
    source_payload = json.loads(source_path.read_text(encoding="utf-8"))
    fields = json.loads(candidate_path.read_text(encoding="utf-8"))
    source_equal = canonical_token_payload(source_payload) == canonical_token_payload(raw_payload)
    records = []
    for field in fields:
        if field.get("status") != "available":
            continue
        indices = [int(x) for x in field.get("source_token_indices", [])]
        selected = [token for token in raw if token["index"] in set(indices)]
        source_text = reading_order_text(selected)
        value = str(field.get("value") or "").strip()
        issues = []
        if not selected:
            issues.append("source_index_missing")
        if selected and source_text != value:
            issues.append("source_value_mismatch")
        if selected and not same_bbox(bbox_union(indices, raw), flatten_bbox(field.get("bbox"))):
            issues.append("bbox_mismatch")
        type_issue = field_type_issue(str(field["field_name"]), value)
        if type_issue:
            issues.append(type_issue)
        records.append({
            "case_id": case_id,
            "document_type": manifest_row["document_type"],
            "source_group": manifest_row["source_group"],
            "field_name": field["field_name"],
            "status": field.get("status"),
            "value": value,
            "source_text": source_text,
            "source_token_indices": json.dumps(indices),
            "gold_bbox": json.dumps(flatten_bbox(field.get("bbox"))),
            "source_bbox": json.dumps(bbox_union(indices, raw)),
            "provenance_source_equal": source_equal,
            "structural_status": "FAIL" if issues else "PASS",
            "structural_issues": ";".join(issues),
            "semantic_status": "CANNOT_VERIFY",
            "semantic_reason": "original TL is word-level and contains no semantic field label",
            "original_tl_zip": str(archive),
            "original_tl_entry": manifest_row["label_entry"],
            "source_annotation": str(source_path),
            "candidate_gold": str(candidate_path),
        })
    row_issues = item_row_audit(fields, raw)
    return records, {"case_id": case_id, "source_token_count": len(raw), "source_payload_token_geometry_equal": source_equal, "item_row_issues": row_issues}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/fintra/devscale1500/manifest.jsonl"))
    parser.add_argument("--training-root", type=Path, default=Path("artifacts/aihub/Training"))
    parser.add_argument("--cases-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    ids = [line.strip() for line in args.allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(ids) != len(set(ids)):
        raise ValueError("allowlist contains duplicate case IDs")
    manifest = load_manifest(args.manifest)
    tl_dir = find_tl_dir(args.training_root)
    records, cases = [], []
    for case_id in ids:
        if case_id not in manifest:
            raise KeyError(case_id)
        current, meta = audit_case(case_id, manifest[case_id], args.cases_root, args.gold_root, tl_dir)
        records.extend(current)
        cases.append(meta)
    args.output_root.mkdir(parents=True, exist_ok=True)
    fields_path = args.output_root / "gold_candidate_integrity_fields.csv"
    columns = list(records[0]) if records else ["case_id"]
    with fields_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    structural = Counter(row["structural_status"] for row in records)
    issue_counts = Counter(issue for row in records for issue in row["structural_issues"].split(";") if issue)
    row_issues = [issue for case in cases for issue in case["item_row_issues"]]
    summary = {
        "cases": len(cases),
        "available_fields": len(records),
        "structural_status": dict(structural),
        "structural_issue_counts": dict(issue_counts),
        "item_row_issue_count": len(row_issues),
        "source_payload_token_geometry_equal_cases": sum(bool(case["source_payload_token_geometry_equal"]) for case in cases),
        "source_annotation_is_downstream_copy": True,
        "original_tl_root": str(tl_dir),
        "gold_root": str(args.gold_root),
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
        "semantic_role_status": "CANNOT_FULLY_VERIFY_FROM_WORD_LEVEL_TL",
        "status": "PASS" if not structural["FAIL"] and not row_issues else "FAIL",
    }
    (args.output_root / "gold_candidate_integrity_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_root / "gold_candidate_integrity_cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

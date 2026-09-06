"""Audit Gold row inventory and source-token coverage without using predictions.

AI-Hub TL is word-level and has no semantic row labels.  This tool therefore
reports the generated row inventory and all mechanically detectable omissions,
but does not invent an expected semantic row count.  That unresolved count is
explicitly marked CANNOT_VERIFY.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    return {
        str(item["stable_sample_id"]): item
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
        for item in [json.loads(line)]
    }


def token_count(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return len(payload.get("bbox", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/fintra/devscale1500/manifest.jsonl"))
    parser.add_argument("--cases-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    ids = [line.strip() for line in args.allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    manifest = load_manifest(args.manifest)
    records: list[dict[str, Any]] = []
    field_inventory: Counter[str] = Counter()
    duplicate_rows = 0
    noncontiguous_rows = 0
    cases_with_no_rows = 0
    for case_id in ids:
        case = args.gold_root / case_id
        fields = json.loads((case / "semantic_gold_fields.json").read_text(encoding="utf-8"))
        source_tokens = json.loads((args.cases_root / case_id / "source_annotation.json").read_text(encoding="utf-8")).get("bbox", [])
        row_map: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
        row_tokens: dict[int, list[int]] = defaultdict(list)
        for field in fields:
            name = str(field["field_name"])
            field_inventory[name.rsplit(".", 1)[-1]] += int(field.get("status") == "available")
            match = re.fullmatch(r"items\[(\d+)\]\.(description|quantity|unit|unit_price|amount)", name)
            if match:
                row = int(match.group(1))
                row_map[row][match.group(2)] = field
                row_tokens[row].extend(int(index) for index in field.get("source_token_indices", []))
        row_ids = sorted(row_map)
        expected = list(range(len(row_ids)))
        contiguous = row_ids == expected
        if row_ids and not contiguous:
            noncontiguous_rows += 1
        if not row_ids:
            cases_with_no_rows += 1
        token_owners: dict[int, set[int]] = defaultdict(set)
        for row, indices in row_tokens.items():
            for index in set(indices):
                token_owners[index].add(row)
        duplicated = sorted(index for index, owners in token_owners.items() if len(owners) > 1)
        if duplicated:
            duplicate_rows += 1
        records.append({
            "case_id": case_id,
            "document_type": manifest[case_id]["document_type"],
            "source_group": str(manifest[case_id]["source_group"]),
            "source_token_count": len(source_tokens),
            "gold_row_count": len(row_ids),
            "gold_row_indices": json.dumps(row_ids),
            "row_indices_contiguous": contiguous,
            "duplicate_source_tokens_across_rows": json.dumps(duplicated),
            "expected_semantic_row_count": "CANNOT_VERIFY",
            "completeness_status": "CANNOT_VERIFY_WITH_WORD_LEVEL_TL",
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "gold_row_completeness.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]) if records else ["case_id"])
        writer.writeheader(); writer.writerows(records)
    summary = {
        "cases": len(records),
        "by_document_type": dict(Counter(row["document_type"] for row in records)),
        "gold_row_count": sum(int(row["gold_row_count"]) for row in records),
        "cases_with_noncontiguous_row_indices": noncontiguous_rows,
        "cases_with_duplicate_source_tokens_across_rows": duplicate_rows,
        "cases_with_no_item_rows": cases_with_no_rows,
        "field_available_inventory": dict(field_inventory),
        "expected_semantic_row_count": "CANNOT_VERIFY",
        "semantic_completeness_status": "CANNOT_VERIFY_WITH_WORD_LEVEL_TL",
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
    }
    (args.output_dir / "gold_completeness_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Compare Modern and Paddle field-evaluation CSVs on the same gold rows."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


MATCH_STATUSES = {"exact_match", "normalized_match"}
TYPE_LABELS = {
    "Commercial Invoice": "CI",
    "Packing List": "Packing",
    "B/L": "B/L",
}


def _rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], row["field_name"]): row for row in csv.DictReader(handle)}


def compare(modern_path: Path, paddle_path: Path) -> dict[str, object]:
    modern, paddle = _rows(modern_path), _rows(paddle_path)
    keys = sorted(set(modern) & set(paddle))
    if not keys:
        raise ValueError("Modern and Paddle CSVs have no common field rows")
    applicable = [key for key in keys if modern[key]["gt_status"] == "available" and paddle[key]["gt_status"] == "available"]

    def matched(rows: dict[tuple[str, str], dict[str, str]], key: tuple[str, str]) -> bool:
        return rows[key]["status"] in MATCH_STATUSES

    modern_count = sum(matched(modern, key) for key in applicable)
    paddle_count = sum(matched(paddle, key) for key in applicable)
    oracle_count = sum(matched(modern, key) or matched(paddle, key) for key in applicable)
    modern_wins = sum(matched(modern, key) and not matched(paddle, key) for key in applicable)
    paddle_wins = sum(matched(paddle, key) and not matched(modern, key) for key in applicable)

    by_type: dict[str, dict[str, object]] = {}
    for document_type, label in TYPE_LABELS.items():
        group = [key for key in applicable if modern[key]["document_type"] == document_type]
        if not group:
            continue
        by_type[label] = {
            "applicable": len(group),
            "modern_recoverable": sum(matched(modern, key) for key in group),
            "paddle_recoverable": sum(matched(paddle, key) for key in group),
            "oracle_union": sum(matched(modern, key) or matched(paddle, key) for key in group),
        }

    status_delta = Counter(
        f"{modern[key]['status']} -> {paddle[key]['status']}" for key in applicable
    )
    return {
        "contract": "same prepared 60-case semantic-v2 gold rows; recoverable means exact or normalized field match",
        "inputs": {"modern": str(modern_path), "paddle": str(paddle_path)},
        "applicable_fields": len(applicable),
        "modern_recoverable": modern_count,
        "paddle_recoverable": paddle_count,
        "oracle_union_recoverable": oracle_count,
        "modern_recoverability": modern_count / len(applicable),
        "paddle_recoverability": paddle_count / len(applicable),
        "oracle_union_recoverability": oracle_count / len(applicable),
        "modern_only_wins": modern_wins,
        "paddle_only_wins": paddle_wins,
        "by_document_type": by_type,
        "status_transitions": dict(status_delta),
        "note": "This compares extractor outcomes on canonical OCR outputs; it is not a character-level OCR metric and does not make the oracle output deployable.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modern", type=Path, required=True)
    parser.add_argument("--paddle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.modern, args.paddle)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "paddle_vs_modern.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Modern vs Paddle field recoverability",
        "",
        f"- Applicable field rows: {report['applicable_fields']}",
        f"- Modern recoverability: {report['modern_recoverability']:.6f}",
        f"- Paddle recoverability: {report['paddle_recoverability']:.6f}",
        f"- Oracle union (diagnostic upper bound): {report['oracle_union_recoverability']:.6f}",
        f"- Modern-only wins: {report['modern_only_wins']}",
        f"- Paddle-only wins: {report['paddle_only_wins']}",
        "",
        "## By document type",
        "",
        "| Type | Applicable | Modern | Paddle | Oracle union |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, values in report["by_document_type"].items():
        lines.append(f"| {label} | {values['applicable']} | {values['modern_recoverable']} | {values['paddle_recoverable']} | {values['oracle_union']} |")
    lines += [
        "",
        "The oracle union is a diagnostic comparison only: it selects the better result after seeing gold and cannot be used as a production backend without a routing policy.",
        "",
        "Status transitions:",
        "",
    ]
    lines.extend(f"- `{key}`: {value}" for key, value in sorted(report["status_transitions"].items()))
    (args.output_dir / "PADDLE_VS_MODERN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

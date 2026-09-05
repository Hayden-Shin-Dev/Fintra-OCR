"""Aggregate per-sample output from the bundled AI-Hub evaluator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _hmean(recall: float, precision: float) -> float:
    return 2 * recall * precision / (recall + precision) if recall + precision else 0.0


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw = {}
    for key in (
        "det_correct_num_recall", "det_correct_num_precision", "chars_gt", "chars_det",
        "e2e_correct_num_recall", "e2e_correct_num_precision", "chars_recog",
        "e2e_recog_score_chars", "e2e_recog_score_correct_num",
        "num_splitted", "num_merged", "num_false_positive", "char_missed",
        "char_overlapped", "char_false_positive", "e2e_char_missed", "e2e_char_false_positive",
    ):
        raw[key] = sum(float(row.get("Rawdata", {}).get(key, 0)) for row in rows)
    det_recall = raw["det_correct_num_recall"] / raw["chars_gt"] if raw["chars_gt"] else 0.0
    det_precision = raw["det_correct_num_precision"] / raw["chars_det"] if raw["chars_det"] else 0.0
    e2e_recall = raw["e2e_correct_num_recall"] / raw["chars_gt"] if raw["chars_gt"] else 0.0
    e2e_precision = raw["e2e_correct_num_precision"] / raw["chars_recog"] if raw["chars_recog"] else 0.0
    return {
        "documents": len(rows),
        "raw": raw,
        "Detection": {"recall": det_recall, "precision": det_precision, "hmean": _hmean(det_recall, det_precision)},
        "EndtoEnd": {
            "recall": e2e_recall,
            "precision": e2e_precision,
            "hmean": _hmean(e2e_recall, e2e_precision),
            "recognition_score": raw["e2e_recog_score_correct_num"] / raw["e2e_recog_score_chars"] if raw["e2e_recog_score_chars"] else 0.0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-root", type=Path, required=True)
    parser.add_argument("--official-output", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    per_sample_dir = args.official_output / "extracted"
    by_type: dict[str, list[dict[str, Any]]] = {}
    all_rows = []
    for case_dir in sorted(args.smoke_root.iterdir()):
        manifest_path = case_dir / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        stem = Path(manifest["image"]).stem
        sample_path = per_sample_dir / f"{stem}.json"
        if not sample_path.is_file():
            raise RuntimeError(f"missing official per-sample result: {sample_path}")
        row = json.loads(sample_path.read_text(encoding="utf-8"))
        doc_type = "Commercial Invoice" if case_dir.name.startswith("ci-") else "Packing List" if case_dir.name.startswith("pl-") else "B/L"
        by_type.setdefault(doc_type, []).append(row)
        all_rows.append(row)
    result = {
        "schema_version": "fintra-ocr-v2.official-aggregate.v1",
        "baseline_name": "AI-Hub original weights/code CPU reference baseline",
        "metric_source": "AI-Hub bundled evaluation_method/script.py",
        "by_document_type": {doc_type: _aggregate(rows) for doc_type, rows in sorted(by_type.items())},
        "overall": _aggregate(all_rows),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "official_metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# AI-Hub bundled official evaluator — 15-document smoke aggregate",
        "",
        "Metric source: `evaluation_method/script.py`; matching uses pseudo-character-center inclusion and area precision constraint 0.5, not polygon IoU.",
        "",
        "| Type | Docs | Detection P | Detection R | Detection Hmean | E2E P | E2E R | E2E Hmean | Recognition score |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for doc_type, item in result["by_document_type"].items():
        d, e = item["Detection"], item["EndtoEnd"]
        lines.append(f"| {doc_type} | {item['documents']} | {d['precision']:.6f} | {d['recall']:.6f} | {d['hmean']:.6f} | {e['precision']:.6f} | {e['recall']:.6f} | {e['hmean']:.6f} | {e['recognition_score']:.6f} |")
    item = result["overall"]
    d, e = item["Detection"], item["EndtoEnd"]
    lines.append(f"| **Overall** | **{item['documents']}** | **{d['precision']:.6f}** | **{d['recall']:.6f}** | **{d['hmean']:.6f}** | **{e['precision']:.6f}** | **{e['recall']:.6f}** | **{e['hmean']:.6f}** | **{e['recognition_score']:.6f}** |")
    (args.output_dir / "official_metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result["overall"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Render the machine-readable RCA report as a human-readable Markdown summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    lines = [
        "# AI-Hub field failure root-cause summary",
        "",
        f"- Failure count: {report['failure_count']}",
        f"- Classification counts: `{json.dumps(report['failure_class_counts'], ensure_ascii=False)}`",
        "- `OCR_MISSING` means the expected value was not sufficiently present in raw OCR; it is not an extractor defect.",
        "- Expected bbox is a semantic GT field bbox only when the reconstructed oracle provides one. Otherwise the report marks it unavailable; matched raw OCR bboxes are listed separately.",
        "",
        "## Failure table",
        "",
        "| document | type | field | class | expected | output | raw evidence | bbox source |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in report["failures"]:
        expected = json.dumps(item.get("oracle_expected_value"), ensure_ascii=False)
        output = json.dumps(item.get("extractor_output"), ensure_ascii=False)
        lines.append(
            f"| {item['document_id']} | {item['document_type']} | {item['field']} | {item['failure_classification']} | {expected} | {output} | {item['expected_text_in_raw_ocr']} | {item['expected_bbox_source']} |"
        )
    lines += ["", "## Per-failure evidence", ""]
    for index, item in enumerate(report["failures"], 1):
        lines += [
            f"### {index}. {item['document_id']} / {item['field']}",
            "",
            f"- Status/class: `{item['failure_classification']}`; extractor status `{item['extractor_status']}`",
            f"- Oracle expected value: `{json.dumps(item.get('oracle_expected_value'), ensure_ascii=False)}`",
            f"- Expected raw text: `{item.get('oracle_expected_raw_text') or ''}`",
            f"- Expected bbox: `{json.dumps(item.get('oracle_expected_bbox'), ensure_ascii=False)}` ({item['expected_bbox_source']})",
            f"- Expected text in raw OCR: `{item['expected_text_in_raw_ocr']}`",
            f"- Raw matches: `{json.dumps(item.get('expected_text_matches'), ensure_ascii=False)}`",
            f"- Selected candidate: `{json.dumps(item.get('selected_candidate'), ensure_ascii=False)}`",
            f"- Stored-vs-reconstructed oracle conflict: `{item.get('oracle_conflict')}`; true failure under reconstructed oracle: `{item.get('true_failure_under_reconstructed_oracle')}`",
            f"- Root cause: {item['root_cause']}",
            "",
        ]
    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"failures": report["failure_count"], "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

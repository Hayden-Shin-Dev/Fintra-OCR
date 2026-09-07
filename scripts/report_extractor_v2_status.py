"""Build a concise, reproducible Extractor v2 status report from artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidate_counts(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return dict(Counter(row["outcome"] for row in csv.DictReader(handle)))


def recoverable_count(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accurate", type=Path, required=True)
    parser.add_argument("--fast", type=Path, required=True)
    parser.add_argument("--v3", type=Path, required=True)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    datasets = {
        "Accurate75": args.accurate,
        "Fast300": args.fast,
        "v3-75": args.v3,
    }
    reports = {}
    for name, root in datasets.items():
        metrics = read_json(root / "field_metrics.json")
        candidate = candidate_counts(root / "candidate_diagnostic.csv")
        reports[name] = {"metrics": metrics, "candidate_outcomes": candidate,
                         "recoverable_but_wrong": recoverable_count(root / "recoverable_but_wrong.csv")}
    oracle = read_json(args.oracle)
    audit = read_json(args.audit)
    lines = [
        "# Extractor v2 status",
        "",
        "This report uses frozen OCR and frozen Gold artifacts. It does not modify either.",
        "",
        "## Overall benchmark",
        "",
        "| Dataset | Documents | Applicable | Correct | Accuracy | OCR recoverable | Recoverable-but-wrong |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, report in reports.items():
        overall = report["metrics"]["overall"]
        ceiling = oracle.get("by_dataset", {}).get(name, {})
        lines.append(f"| {name} | {report['metrics']['selection']['documents']} | {overall['applicable_gold']} | {overall['normalized_matches']} | {pct(overall['normalized_field_accuracy'])} | {ceiling.get('recoverable', 'n/a')} | {report['recoverable_but_wrong']} |")
    lines += ["", "## Document-type accuracy", "", "| Dataset | Type | Applicable | Correct | Accuracy |", "|---|---|---:|---:|---:|"]
    for name, report in reports.items():
        for doc_type, values in report["metrics"]["by_document_type"].items():
            lines.append(f"| {name} | {doc_type} | {values['applicable_gold']} | {values['normalized_matches']} | {pct(values['normalized_field_accuracy'])} |")
    lines += ["", "## Candidate decision evidence", "", "| Dataset | Candidate improves | Candidate regression | Candidate missing | Both correct | Both wrong |", "|---|---:|---:|---:|---:|---:|"]
    for name, report in reports.items():
        counts = report["candidate_outcomes"]
        lines.append(f"| {name} | {counts.get('CANDIDATE_IMPROVES', 0)} | {counts.get('CANDIDATE_REGRESSION', 0)} | {counts.get('CANDIDATE_MISSING', 0)} | {counts.get('BOTH_CORRECT', 0)} | {counts.get('BOTH_WRONG', 0)} |")
    lines += ["", "## Field metrics", ""]
    for name, report in reports.items():
        lines += [f"### {name}", "", "| Field | Applicable | Correct | Wrong | Missing | Accuracy |", "|---|---:|---:|---:|---:|---:|"]
        for field, values in sorted(report["metrics"]["by_field"].items()):
            if values["applicable_gold"]:
                lines.append(f"| {field} | {values['applicable_gold']} | {values['normalized_matches']} | {values['wrong']} | {values['missing']} | {pct(values['normalized_field_accuracy'])} |")
        lines.append("")
    lines += [
        "## OCR ceiling note", "",
        "The oracle artifact is an evidence upper-bound diagnostic, not character accuracy. It is computed from the frozen OCR regions and Gold token geometry; it must not be conflated with extractor accuracy.",
        "",
        "## Static production audit", "",
        f"- passed: `{audit.get('passed')}`",
        f"- active dispatch clean: `{audit.get('active_dispatch_clean')}`",
        f"- absolute template helpers on primary path: `{audit.get('absolute_template_helpers_on_primary_path')}`",
        f"- clean call graph: `{', '.join(audit.get('clean_call_graph', []))}`",
        "",
        "## Decision",
        "",
        "The active v2 path is schema-complete and testable, but it is not an 80% universal extractor yet. Candidate arbitration remains conservative because the frozen benchmark shows substantially more candidate regressions than candidate improvements. Further generalized resolver work is required; no Gold/OCR tuning is justified by these artifacts.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"REPORT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

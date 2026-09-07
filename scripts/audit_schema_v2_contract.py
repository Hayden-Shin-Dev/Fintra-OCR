"""Audit the Audit Field Schema v2 inventory against the output contract.

This is a contract audit only.  It does not run OCR, read Gold, or invoke an
extractor.  The checked-in schema artifact remains the source of truth for
the intended field inventory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.extraction.v2.specs import DOCUMENT_FIELDS, ITEM_FIELDS, SPECS


def _artifact_fields(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(artifact: Path) -> dict:
    payload = _artifact_fields(artifact)
    intended = sorted({item["canonical_name"] for item in payload["fields"]})
    defined = sorted(SPECS)
    wired_document = sorted({name for names in DOCUMENT_FIELDS.values() for name in names})
    wired_item = sorted({name for names in ITEM_FIELDS.values() for name in names})
    wired = sorted(set(wired_document) | set(wired_item))
    return {
        "source_of_truth": str(artifact),
        "intended_count": len(intended),
        "defined_count": len(defined),
        "wired_document_count": len(wired_document),
        "wired_item_count": len(wired_item),
        "wired_unique_count": len(wired),
        "missing_from_specs": sorted(set(intended) - set(defined)),
        "extra_specs_not_in_artifact": sorted(set(defined) - set(intended)),
        "missing_from_output": sorted(set(intended) - set(wired)),
        "extra_output_fields_not_in_artifact": sorted(set(wired) - set(intended)),
        "document_field_counts": {key: len(value) for key, value in DOCUMENT_FIELDS.items()},
        "item_field_counts": {key: len(value) for key, value in ITEM_FIELDS.items()},
        "document_fields": {key: list(value) for key, value in DOCUMENT_FIELDS.items()},
        "item_fields": {key: list(value) for key, value in ITEM_FIELDS.items()},
        "status": "PASS" if set(intended) == set(defined) == set(wired) else "FAIL",
    }


def write_report(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "schema_contract_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Audit Field Schema v2 contract audit",
        "",
        f"- Source of truth: `{report['source_of_truth']}`",
        f"- Status: **{report['status']}**",
        "",
        "## Inventory",
        "",
        f"- Intended fields: {report['intended_count']}",
        f"- SPECS-defined fields: {report['defined_count']}",
        f"- Wired document fields: {report['wired_document_count']}",
        f"- Wired item fields: {report['wired_item_count']}",
        f"- Wired unique fields: {report['wired_unique_count']}",
        f"- Missing from SPECS: {', '.join(report['missing_from_specs']) or 'none'}",
        f"- Missing from output: {', '.join(report['missing_from_output']) or 'none'}",
        "",
        "## Contract slots",
        "",
    ]
    for doc in ("Commercial Invoice", "Packing List", "B/L"):
        lines.append(f"- {doc}: {report['document_field_counts'][doc]} document + {report['item_field_counts'].get(doc, 0)} item fields")
    (output_dir / "SCHEMA_V2_CONTRACT_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("artifacts/fintra/schema-v2/field_schema_v2.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/fintra/schema-v2"),
    )
    args = parser.parse_args()
    report = audit(args.artifact)
    write_report(report, args.output_dir)
    print(json.dumps({key: report[key] for key in (
        "intended_count", "defined_count", "wired_document_count",
        "wired_item_count", "wired_unique_count", "missing_from_specs",
        "missing_from_output", "status",
    )}, ensure_ascii=False))


if __name__ == "__main__":
    main()

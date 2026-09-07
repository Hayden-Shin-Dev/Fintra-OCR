"""Write the schema-v2 resolver activity matrix without running OCR."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.extraction.v2.specs import (  # noqa: E402
    COMPATIBILITY_DOCUMENT_FIELDS,
    DOCUMENT_FIELDS,
    FIELD_FAMILY,
    ITEM_FIELDS,
)


def build() -> dict:
    result = {}
    for document_type in DOCUMENT_FIELDS:
        result[document_type] = {
            "document_fields": [
                {"field": name, "status": "active", "family": FIELD_FAMILY.get(name, "scalar")}
                for name in DOCUMENT_FIELDS[document_type]
            ],
            "item_fields": [
                {"field": name, "status": "active", "family": "table"}
                for name in ITEM_FIELDS.get(document_type, ())
            ],
            "compatibility_only": [
                {"field": name, "status": "compatibility_only", "family": "scalar"}
                for name in COMPATIBILITY_DOCUMENT_FIELDS.get(document_type, ())
            ],
        }
    return {"schema_version": "fintra-audit-field-schema-v2", "documents": result}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/fintra/schema-v2/field_activity.json"))
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build()
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()

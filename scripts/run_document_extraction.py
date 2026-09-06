"""CLI: document file + configured OCR adapter -> canonical JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fintra.ocr.adapter import CommandOCRAdapter, FixtureOCRAdapter
from fintra.services.document_service import DOCUMENT_TYPES, extract_document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--document-type", choices=DOCUMENT_TYPES, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--ocr-fixture-dir", type=Path)
    source.add_argument(
        "--ocr-command",
        help=("Command template containing {document_path}, {document_type}, "
              "and {output_json}; its output is consumed as canonical OCR JSON."),
    )
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    adapter = (
        FixtureOCRAdapter(args.ocr_fixture_dir)
        if args.ocr_fixture_dir is not None
        else CommandOCRAdapter(args.ocr_command, work_dir=args.work_dir)
    )
    payload = extract_document(args.document, args.document_type, adapter)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()

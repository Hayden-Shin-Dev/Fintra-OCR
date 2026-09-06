"""Reclassify known Gold defects conservatively using source-only evidence.

The historical known-defect report recorded old/new differences as verified
errors. This audit does not make that inference. Without a semantic role in
the original TL, a changed value is retained as unresolved/CANNOT_VERIFY.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records: list[dict[str, Any]] = json.loads(args.input.read_text(encoding="utf-8"))
    audited = []
    for record in records:
        item = dict(record)
        item["prior_classification"] = item.get("classification")
        item["classification"] = "CANNOT_VERIFY"
        item["semantic_reason"] = (
            "Original AI-Hub TL entry is word-level and has no semantic role label; "
            "old/new Gold token changes alone do not prove the canonical field meaning. "
            "Image/header/layout semantic sign-off is not present in this artifact."
        )
        item["prediction_blind"] = True
        item["ocr_read"] = False
        item["extractor_read"] = False
        item["final_holdout_2_accessed"] = False
        audited.append(item)
    result = {
        "records": len(audited),
        "classifications": {"CANNOT_VERIFY": len(audited)},
        "input": str(args.input),
        "output": str(args.output),
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"metrics": result, "records": audited}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(
        "\n".join([
            "# Known-defect semantic closure",
            "",
            "This is a conservative source-only closure. It does not treat an old/new Gold difference as proof of a mapping error.",
            "",
            f"- Records audited: {len(audited)}",
            "- Classification: CANNOT_VERIFY for every record",
            "- Reason: original Training TL is word-level and carries no semantic role label; exhaustive image/header/layout sign-off is not encoded.",
            "- FINAL-HOLDOUT #2 accessed: false",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

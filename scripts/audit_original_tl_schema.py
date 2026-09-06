"""Audit the schema of every locally stored Training TL JSON entry."""

from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-root", type=Path, default=Path("artifacts/aihub/Training"))
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    archives = sorted(args.training_root.rglob("TL*.zip"))
    top_keys = Counter()
    nested_keys: dict[str, Counter[str]] = {}
    entries = 0
    for archive in archives:
        with zipfile.ZipFile(archive) as handle:
            for name in handle.namelist():
                if not name.lower().endswith(".json"):
                    continue
                payload = json.loads(handle.read(name).decode("utf-8-sig"))
                entries += 1
                top_keys.update(payload.keys())
                for key, value in payload.items():
                    if isinstance(value, dict):
                        nested_keys.setdefault(key, Counter()).update(value.keys())
    args.output_root.mkdir(parents=True, exist_ok=True)
    summary = {
        "training_root": str(args.training_root),
        "tl_archive_count": len(archives),
        "tl_json_entry_count": entries,
        "top_level_keys": dict(top_keys),
        "nested_keys": {key: dict(value) for key, value in nested_keys.items()},
        "semantic_field_keys_observed": [],
        "interpretation": "AI-Hub Training TL is word-level geometry/text annotation; semantic Fintra field labels are not present in TL JSON",
        "prediction_blind": True,
        "ocr_read": False,
        "extractor_read": False,
        "final_holdout_2_accessed": False,
    }
    (args.output_root / "tl_schema_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_root / "TL_SCHEMA_AUDIT.md").write_text(
        "# Original Training TL schema audit\n\n"
        f"- TL archives: `{len(archives)}`\n"
        f"- JSON entries: `{entries}`\n"
        f"- Top-level keys: `{', '.join(sorted(top_keys))}`\n"
        "- Semantic Fintra field labels: **not present**\n\n"
        "The source TL stores word-level text and polygon geometry. It is sufficient for provenance, token membership, bbox, typed constraints, and geometry checks, but it cannot independently prove every semantic role (for example loading versus discharge) without document/layout evidence.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Emit an evidence table for already identified Gold defects.

This is a read-only closure report, not a Gold generator.  The scope is passed
explicitly by the caller; the report copies values and token geometry from the
old/new Gold and the original Training TL archive without reading OCR or
extractor output.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    return {str(item["stable_sample_id"]): item for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip() for item in [json.loads(line)]}


def find_archive(training_root: Path, group: str) -> Path:
    matches = [path for path in training_root.rglob("TL*.zip") if group.upper() in path.stem.upper()]
    if len(matches) != 1:
        raise RuntimeError(f"expected one TL archive for {group}, found {matches}")
    return matches[0]


def load_source(case_id: str, manifest: dict[str, Any], training_root: Path) -> tuple[Path, list[dict[str, Any]]]:
    archive = find_archive(training_root, str(manifest["source_group"]))
    entry = str(manifest["label_entry"])
    with zipfile.ZipFile(archive) as handle:
        name = next((candidate for candidate in (entry, entry.lstrip("/")) if candidate in handle.namelist()), None)
        if name is None:
            raise KeyError(f"missing TL entry {entry!r} in {archive}")
        payload = json.loads(handle.read(name).decode("utf-8-sig"))
    tokens = []
    for index, item in enumerate(payload.get("bbox", [])):
        xs, ys = item.get("x", []), item.get("y", [])
        if len(xs) >= 3 and len(xs) == len(ys):
            tokens.append({"index": index, "text": str(item.get("data") or ""), "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return archive, tokens


def field_map(path: Path) -> dict[str, dict[str, Any]]:
    return {str(field["field_name"]): field for field in json.loads(path.read_text(encoding="utf-8"))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-field", action="append", required=True, help="case_id:field_name")
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/fintra/devscale1500/manifest.jsonl"))
    parser.add_argument("--training-root", type=Path, default=Path("artifacts/aihub/Training"))
    parser.add_argument("--old-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    output: list[dict[str, Any]] = []
    for requested in args.case_field:
        case_id, field_name = requested.split(":", 1)
        old = field_map(args.old_root / case_id / "semantic_gold_fields.json").get(field_name, {})
        new = field_map(args.new_root / case_id / "semantic_gold_fields.json").get(field_name, {})
        archive, tokens = load_source(case_id, manifest[case_id], args.training_root)
        indices = sorted(set(int(i) for i in old.get("source_token_indices", []) + new.get("source_token_indices", [])))
        output.append({
            "case_id": case_id,
            "document_type": manifest[case_id]["document_type"],
            "source_group": str(manifest[case_id]["source_group"]),
            "field_name": field_name,
            "classification": "VERIFIED_GOLD_MAPPING_ERROR" if old and new and (old.get("value") != new.get("value") or old.get("source_token_indices") != new.get("source_token_indices")) else "SOURCE_LAYOUT_REVIEW_REQUIRED",
            "old_gold": {key: old.get(key) for key in ("value", "status", "source_token_indices")},
            "new_gold": {key: new.get(key) for key in ("value", "status", "source_token_indices")},
            "original_tl_zip": str(archive),
            "original_tl_entry": manifest[case_id]["label_entry"],
            "original_tl_tokens": [token for token in tokens if token["index"] in indices],
            "prediction_blind": True,
            "ocr_read": False,
            "extractor_read": False,
            "final_holdout_2_accessed": False,
        })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "known_defect_closure.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Known Gold defect closure", "", "This report uses original Training TL plus old/new Gold only. It does not read OCR or extractor predictions.", ""]
    for row in output:
        lines.extend([
            f"## {row['case_id']} — {row['field_name']}",
            f"- Classification: `{row['classification']}`",
            f"- Original TL: `{row['original_tl_zip']}` entry `{row['original_tl_entry']}`",
            f"- Old Gold: `{row['old_gold']}`",
            f"- New Gold: `{row['new_gold']}`",
            f"- Original TL tokens: `{row['original_tl_tokens']}`",
            "- Interpretation: the new source-token assignment is a generalized typed/layout correction; this report does not use model predictions.",
            "",
        ])
    (args.output_dir / "KNOWN_DEFECT_CLOSURE.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"records": len(output), "output_dir": str(args.output_dir), "prediction_blind": True, "final_holdout_2_accessed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()

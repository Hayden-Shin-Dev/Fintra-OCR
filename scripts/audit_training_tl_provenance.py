"""Audit Accurate75 #1 provenance against the local AI-Hub Training TL archives.

The audit reads only the Accurate75 #1 allowlist.  It opens each original TL
JSON directly from its ZIP and compares it with the devscale label and the
case ``source_annotation.json``.  It intentionally does not read any final
holdout allowlist or output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            result[str(row["stable_sample_id"])] = row
    return result


def token_signature(payload: dict[str, Any]) -> tuple[list[str], list[tuple[Any, Any]]]:
    tokens = payload.get("bbox", [])
    return (
        [str(item.get("data", "")) for item in tokens],
        [(item.get("x"), item.get("y")) for item in tokens],
    )


def find_tl_archive(tl_root: Path, source_group: str) -> Path:
    matches = sorted(tl_root.glob(f"TL*{source_group}.zip"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one TL archive for {source_group}, found {len(matches)}: {matches}"
        )
    return matches[0]


def audit_case(
    *,
    case_id: str,
    row: dict[str, Any],
    tl_root: Path,
    devscale_root: Path,
    case_root: Path,
) -> dict[str, Any]:
    archive = find_tl_archive(tl_root, str(row["source_group"]))
    entry = str(row["label_entry"])
    with zipfile.ZipFile(archive) as handle:
        raw_bytes = handle.read(entry)
    dev_path = devscale_root / str(row["label_path"])
    source_path = case_root / case_id / "source_annotation.json"
    dev_bytes = dev_path.read_bytes()
    source_bytes = source_path.read_bytes()
    raw = json.loads(raw_bytes.decode("utf-8-sig"))
    dev = json.loads(dev_bytes.decode("utf-8"))
    source = json.loads(source_bytes.decode("utf-8"))
    raw_text, raw_geometry = token_signature(raw)
    dev_text, dev_geometry = token_signature(dev)
    source_text, source_geometry = token_signature(source)
    parsed_equal = raw == dev == source
    text_equal = raw_text == dev_text == source_text
    geometry_equal = raw_geometry == dev_geometry == source_geometry
    if parsed_equal:
        classification = "A_PARSED_CONTENT_IDENTICAL_SERIALIZATION_DIFF"
    elif text_equal and geometry_equal:
        classification = "B_STRUCTURAL_METADATA_DIFFERENCE"
    else:
        classification = "C_ANNOTATION_CONTENT_DIFFERENCE"
    return {
        "case_id": case_id,
        "document_type": row["document_type"],
        "source_group": row["source_group"],
        "original_tl_zip": str(archive),
        "original_tl_entry": entry,
        "devscale_label": str(dev_path),
        "source_annotation": str(source_path),
        "original_bytes": len(raw_bytes),
        "devscale_bytes": len(dev_bytes),
        "source_annotation_bytes": len(source_bytes),
        "original_sha256": sha256_bytes(raw_bytes),
        "devscale_sha256": sha256_bytes(dev_bytes),
        "source_annotation_sha256": sha256_bytes(source_bytes),
        "original_vs_devscale_byte_equal": raw_bytes == dev_bytes,
        "original_vs_source_annotation_byte_equal": raw_bytes == source_bytes,
        "parsed_content_equal": parsed_equal,
        "token_text_equal": text_equal,
        "token_geometry_equal": geometry_equal,
        "original_token_count": len(raw.get("bbox", [])),
        "devscale_token_count": len(dev.get("bbox", [])),
        "source_annotation_token_count": len(source.get("bbox", [])),
        "classification": classification,
    }


def write_outputs(records: list[dict[str, Any]], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "accurate75_provenance.json").write_text(
        json.dumps(
            {
                "scope": "Accurate75 #1 only",
                "prediction_blind": True,
                "final_holdout_2_accessed": False,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    columns = list(records[0]) if records else []
    with (output_root / "accurate75_provenance.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    counts: dict[str, int] = {}
    for record in records:
        key = str(record["classification"])
        counts[key] = counts.get(key, 0) + 1
    by_type: dict[str, int] = {}
    by_group: dict[str, int] = {}
    for record in records:
        by_type[str(record["document_type"])] = by_type.get(str(record["document_type"]), 0) + 1
        by_group[str(record["source_group"])] = by_group.get(str(record["source_group"]), 0) + 1
    report = [
        "# Accurate75 #1 Training TL provenance",
        "",
        "This is a prediction-blind provenance audit of the Accurate75 #1 allowlist.",
        "The final holdout #2 was not read or inspected.",
        "",
        f"- Cases audited: {len(records)}",
        f"- Classifications: `{json.dumps(counts, ensure_ascii=False, sort_keys=True)}`",
        f"- Document types: `{json.dumps(by_type, ensure_ascii=False, sort_keys=True)}`",
        f"- Source groups: `{json.dumps(by_group, ensure_ascii=False, sort_keys=True)}`",
        "- Original TL JSON was read directly from each local Training TL ZIP entry.",
        "- `devscale1500/labels` and `source_annotation.json` are downstream JSON files.",
        "- All 75 cases must be parsed-content, token-text, and token-geometry equal.",
        "",
        "## Classification semantics",
        "",
        "- `A_PARSED_CONTENT_IDENTICAL_SERIALIZATION_DIFF`: JSON objects equal after parsing; byte serialization differs.",
        "- `B_STRUCTURAL_METADATA_DIFFERENCE`: token text and geometry equal but other structure differs.",
        "- `C_ANNOTATION_CONTENT_DIFFERENCE`: annotation content or geometry differs.",
        "",
    ]
    (output_root / "TRAINING_TL_PROVENANCE.md").write_text(
        "\n".join(report), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path("artifacts/fintra/train-scale-v1/parallel/accurate-balanced75.txt"),
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("artifacts/fintra/devscale1500/manifest.jsonl")
    )
    parser.add_argument("--tl-root", type=Path, default=Path("artifacts/aihub/Training/02.라벨링데이터"))
    parser.add_argument("--devscale-root", type=Path, default=Path("artifacts/fintra/devscale1500"))
    parser.add_argument("--case-root", type=Path, default=Path("artifacts/fintra/train-scale-v1/cases"))
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/fintra/gold_audit/training-tl-provenance"),
    )
    args = parser.parse_args()
    ids = [line.strip() for line in args.allowlist.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(ids) != 75 or len(set(ids)) != 75:
        raise ValueError(f"Accurate75 #1 allowlist must contain 75 unique IDs, got {len(ids)}")
    manifest = load_manifest(args.manifest)
    missing = [case_id for case_id in ids if case_id not in manifest]
    if missing:
        raise KeyError(f"Missing manifest rows: {missing[:5]}")
    records = [
        audit_case(
            case_id=case_id,
            row=manifest[case_id],
            tl_root=args.tl_root,
            devscale_root=args.devscale_root,
            case_root=args.case_root,
        )
        for case_id in ids
    ]
    write_outputs(records, args.output_root)
    counts: dict[str, int] = {}
    for record in records:
        key = str(record["classification"])
        counts[key] = counts.get(key, 0) + 1
    print(json.dumps({"cases": len(records), "classifications": counts, "output_root": str(args.output_root)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

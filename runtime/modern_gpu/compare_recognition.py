"""Compare Modern Recognition TXT with the existing CPU reference TXT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_txt(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            fields = line.split(",", 8)
            rows.append({"bbox": [int(float(x)) for x in fields[:8]], "text": fields[8]})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--modern", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    reference = read_txt(args.reference)
    modern = read_txt(args.modern)
    changed = []
    for index in range(max(len(reference), len(modern))):
        left = reference[index] if index < len(reference) else None
        right = modern[index] if index < len(modern) else None
        if left != right:
            changed.append({"index": index, "reference": left, "modern": right})
    exact = sum(1 for left, right in zip(reference, modern) if left == right)
    result = {
        "reference_regions": len(reference),
        "modern_regions": len(modern),
        "changed_regions": len(changed),
        "exact_ordered_regions": exact,
        "empty_modern_text": sum(1 for row in modern if not row["text"]),
        "parity": not changed and len(reference) == len(modern),
        "changes": changed,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["parity"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()


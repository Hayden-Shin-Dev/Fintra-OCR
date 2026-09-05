"""Normalize one or more unmodified AI-Hub official OCR TXT outputs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "fintra-ocr-v2.raw-predictions.v2"


def _number(value: str) -> int | float:
    number = float(value.strip())
    if not math.isfinite(number):
        raise ValueError("coordinate is not finite")
    return int(number) if number.is_integer() else number


def parse_prediction_file(path: Path) -> dict[str, Any]:
    predictions: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw_line.strip():
            continue
        fields = raw_line.split(",", 8)
        if len(fields) != 9:
            raise ValueError(
                f"{path}:{line_number}: expected 8 coordinates and text, "
                f"got {len(fields)} fields"
            )
        try:
            coordinates = [_number(value) for value in fields[:8]]
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: invalid coordinate") from exc
        predictions.append(
            {
                "index": len(predictions),
                "polygon": [
                    [coordinates[0], coordinates[1]],
                    [coordinates[2], coordinates[3]],
                    [coordinates[4], coordinates[5]],
                    [coordinates[6], coordinates[7]],
                ],
                "text": fields[8],
                "raw_line": raw_line,
            }
        )
    return {
        "image_stem": path.stem,
        "predictions": predictions,
        "source_file": str(path),
    }


def normalize(input_path: Path) -> dict[str, Any]:
    files = [input_path] if input_path.is_file() else sorted(input_path.rglob("*.txt"))
    if not files:
        raise ValueError(f"no TXT prediction files found under {input_path}")
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {"format": "aihub-official-txt", "input": str(input_path)},
        "documents": [parse_prediction_file(path) for path in files],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = normalize(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"normalized {len(result['documents'])} document(s) -> {args.output}")


if __name__ == "__main__":
    main()

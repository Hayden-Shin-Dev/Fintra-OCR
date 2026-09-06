"""Prepare Paddle output for the exact 15-document AI-Hub golden set."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fintra.ocr.adapter import OCRResult
from scripts.build_official_eval_inputs import _gt_lines


GOLDEN_CASES = (
    "ci-001", "ci-005", "ci-009", "ci-013", "ci-017",
    "pl-001", "pl-005", "pl-009", "pl-013", "pl-017",
    "bl-001", "bl-005", "bl-009", "bl-013", "bl-017",
)

COMMA_ESCAPE = "\uC27C\uD45C"


def _paddle_lines(path: Path) -> str:
    result = OCRResult.from_json(path, preserve_raw=False)
    lines = []
    for region in result.regions:
        coordinates = ",".join(str(int(round(value))) for point in region.polygon for value in point)
        text = region.text.replace(",", COMMA_ESCAPE).replace("\n", " ")
        lines.append(f"{coordinates},{text}\n")
    return "".join(lines)


def build(cases_root: Path, paddle_root: Path, output_dir: Path) -> None:
    gt_dir, submission_dir = output_dir / "gt", output_dir / "submission"
    gt_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case_id in GOLDEN_CASES:
        case = cases_root / case_id
        manifest_path = case / "case_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        manifest_item = json.loads(manifest_path.read_text(encoding="utf-8"))
        gt_stem, gt_text = _gt_lines(case / "gt.json")
        paddle_path = paddle_root / case_id / "outputs" / "recognition" / "paddle.json"
        if not paddle_path.is_file():
            raise FileNotFoundError(paddle_path)
        (gt_dir / f"gt_{gt_stem}.txt").write_text(gt_text, encoding="utf-8")
        (submission_dir / f"res_{gt_stem}.txt").write_text(_paddle_lines(paddle_path), encoding="utf-8")
        manifest.append({"case_id": case_id, "image_stem": gt_stem, "document_type": manifest_item["document_type"]})
    for archive_path, source_dir in ((output_dir / "gt.zip", gt_dir), (output_dir / "submission.zip", submission_dir)):
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(source_dir.iterdir()):
                archive.write(source, source.name)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CASES={len(manifest)}")
    print(f"GT_ZIP={output_dir / 'gt.zip'}")
    print(f"SUBMISSION_ZIP={output_dir / 'submission.zip'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("artifacts/fintra/field_eval/cases"))
    parser.add_argument("--paddle-cases", type=Path, default=Path("artifacts/fintra/paddle_gpu_field_eval/cases"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fintra/paddle_official_15"))
    args = parser.parse_args()
    build(args.cases, args.paddle_cases, args.output_dir)


if __name__ == "__main__":
    main()

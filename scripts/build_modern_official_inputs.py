"""Build official-evaluator ZIPs from Modern Detection -> Recognition TXT files."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from build_official_eval_inputs import _gt_lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-root", type=Path, required=True)
    parser.add_argument("--modern-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    gt_dir = args.output_dir / "gt"
    submission_dir = args.output_dir / "submission"
    gt_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    case_dirs = sorted(
        path for path in args.smoke_root.iterdir()
        if path.is_dir() and (path / "case_manifest.json").is_file()
    )
    if not case_dirs:
        raise RuntimeError(f"no prepared smoke cases found under {args.smoke_root}")

    for case_dir in case_dirs:
        case_manifest = json.loads(
            (case_dir / "case_manifest.json").read_text(encoding="utf-8")
        )
        image_name = case_manifest["image"]
        image_stem = Path(image_name).stem
        gt_candidates = sorted((case_dir / "source_gt").glob("*.json"))
        if len(gt_candidates) != 1:
            raise RuntimeError(
                f"expected exactly one source GT JSON for {case_dir.name}, "
                f"found {len(gt_candidates)}"
            )

        modern_txt = args.modern_root / case_dir.name / "recognition" / f"{image_stem}.txt"
        if not modern_txt.is_file():
            raise RuntimeError(f"missing Modern E2E TXT: {modern_txt}")

        gt_stem, gt_text = _gt_lines(gt_candidates[0])
        if gt_stem != image_stem:
            raise RuntimeError(
                f"GT/image stem mismatch for {case_dir.name}: "
                f"GT={gt_stem}, image={image_stem}"
            )
        (gt_dir / f"gt_{gt_stem}.txt").write_text(gt_text, encoding="utf-8")
        (submission_dir / f"res_{gt_stem}.txt").write_text(
            modern_txt.read_text(encoding="utf-8"), encoding="utf-8"
        )
        manifest_rows.append(
            {
                "case_id": case_dir.name,
                "image": image_name,
                "image_stem": image_stem,
                "gt_json": str(gt_candidates[0]),
                "modern_txt": str(modern_txt),
            }
        )

    for archive_path, source_dir in (
        (args.output_dir / "gt.zip", gt_dir),
        (args.output_dir / "submission.zip", submission_dir),
    ):
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(source_dir.glob("*.txt")):
                archive.write(source, source.name)

    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"CASES={len(manifest_rows)}")
    print(f"GT_ZIP={args.output_dir / 'gt.zip'}")
    print(f"SUBMISSION_ZIP={args.output_dir / 'submission.zip'}")


if __name__ == "__main__":
    main()

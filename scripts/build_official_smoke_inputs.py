"""Build bundled AI-Hub evaluator ZIPs for all prepared smoke cases."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from build_official_eval_inputs import _gt_lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    gt_dir, submission_dir = args.output_dir / "gt", args.output_dir / "submission"
    gt_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case_dir in sorted(args.smoke_root.iterdir()):
        if not (case_dir / "case_manifest.json").is_file():
            continue
        gt_path = next((case_dir / "source_gt").glob("*.json"))
        raw_path = next((case_dir / "transit_train" / "2023-01-22_latest_test").glob("*.txt"))
        stem, gt_text = _gt_lines(gt_path)
        (gt_dir / f"gt_{stem}.txt").write_text(gt_text, encoding="utf-8")
        (submission_dir / f"res_{stem}.txt").write_text(raw_path.read_text(encoding="utf-8"), encoding="utf-8")
        manifest.append({"case_id": case_dir.name, "image_stem": stem})
    for archive_path, source_dir in ((args.output_dir / "gt.zip", gt_dir), (args.output_dir / "submission.zip", submission_dir)):
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(source_dir.iterdir()):
                archive.write(source, source.name)
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"CASES={len(manifest)}")
    print(f"GT_ZIP={args.output_dir / 'gt.zip'}")
    print(f"SUBMISSION_ZIP={args.output_dir / 'submission.zip'}")


if __name__ == "__main__":
    main()

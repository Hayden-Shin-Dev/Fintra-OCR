"""Build standard AI-Hub evaluator ZIPs from one real Validation case."""

from __future__ import annotations

import argparse
import json
import math
import zipfile
from pathlib import Path


def _ordered_points(xs, ys):
    points = [(float(x), float(y)) for x, y in zip(xs, ys)]
    center_x = sum(point[0] for point in points) / len(points)
    center_y = sum(point[1] for point in points) / len(points)
    return sorted(points, key=lambda point: math.atan2(point[1] - center_y, point[0] - center_x))


def _gt_lines(gt_path: Path) -> tuple[str, str]:
    payload = json.loads(gt_path.read_text(encoding="utf-8"))
    stem = str(payload["Images"]["identifier"])
    lines = []
    for item in payload.get("bbox", []):
        points = _ordered_points(item["x"], item["y"])
        coordinates = ",".join(str(int(round(value))) for point in points for value in point)
        text = "" if item.get("data") is None else str(item["data"])
        lines.append(f"{coordinates},{text.replace(',', '쉼표')}\n")
    return stem, "".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gt-json", type=Path, required=True)
    parser.add_argument("--raw-txt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    stem, gt_text = _gt_lines(args.gt_json)
    gt_dir = args.output_dir / "gt"
    submission_dir = args.output_dir / "submission"
    gt_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)
    gt_file = gt_dir / f"gt_{stem}.txt"
    submission_file = submission_dir / f"res_{stem}.txt"
    gt_file.write_text(gt_text, encoding="utf-8")
    submission_file.write_text(args.raw_txt.read_text(encoding="utf-8"), encoding="utf-8")

    for archive_path, source_dir in ((args.output_dir / "gt.zip", gt_dir), (args.output_dir / "submission.zip", submission_dir)):
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(source_dir.iterdir()):
                archive.write(source, source.name)
    print(f"GT={gt_file}")
    print(f"SUBMISSION={submission_file}")
    print(f"GT_ZIP={args.output_dir / 'gt.zip'}")
    print(f"SUBMISSION_ZIP={args.output_dir / 'submission.zip'}")


if __name__ == "__main__":
    main()

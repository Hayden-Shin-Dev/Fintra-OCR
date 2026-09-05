"""Create a hash inventory for the extracted original Detection reference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_tree(rows: list[dict[str, str]], root: Path, source_root: str, role: str) -> None:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        rows.append(
            {
                "local": path.as_posix(),
                "source": f"{source_root}/{relative}",
                "bytes": str(path.stat().st_size),
                "sha256": sha256(path),
                "role": role,
            }
        )


def add_file(rows: list[dict[str, str]], path: Path, source: str, role: str) -> None:
    if not path.is_file():
        return
    rows.append(
        {
            "local": path.as_posix(),
            "source": source,
            "bytes": str(path.stat().st_size),
            "sha256": sha256(path),
            "role": role,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ref = args.project_root / "artifacts/aihub/reference/original_detection"
    rows: list[dict[str, str]] = []

    add_tree(rows, ref / "transit_detection", "/workspace/transit_detection", "original Detection config")
    add_file(rows, ref / "run_transit.sh", "/workspace/run_transit.sh", "original pipeline entrypoint")
    add_file(rows, ref / "text_recognition_baseline/detection_model.py", "/workspace/text_recognition_baseline/detection_model.py", "original Detection-to-Recognition wrapper")
    add_tree(rows, ref / "text_recognition_baseline/new_detection", "/workspace/text_recognition_baseline/new_detection", "original MMDetection/MMOCR Detection source and configs")
    add_tree(rows, ref / "text_recognition_baseline/evaluation_method", "/workspace/text_recognition_baseline/evaluation_method", "bundled AI-Hub official evaluator")
    add_tree(rows, ref / "model_store", "/workspace/model_store", "original Detection metadata")

    runtime = args.project_root / "artifacts/aihub/runtime"
    add_file(rows, runtime / "transit_detection_model.pth", "/workspace/model_store/transit_detection_model.pth", "original Detection checkpoint")

    smoke = args.project_root / "artifacts/aihub/validation/smoke"
    for case in sorted(path for path in smoke.iterdir() if path.is_dir() and path.name[:3] in {"ci-", "pl-", "bl-"}):
        manifest_path = case / "case_manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        stem = Path(manifest["image"]).stem
        add_file(
            rows,
            case / "transit_train/transit_detection_result_latest.pkl",
            "/workspace/images/transit_train/transit_detection_result_latest.pkl",
            f"CPU golden original Detection PKL ({case.name})",
        )
        add_file(
            rows,
            case / f"transit_train/2023-01-22_latest_test/{stem}.txt",
            f"/workspace/images/transit_train/2023-01-22_latest_test/{stem}.txt",
            f"CPU golden original OCR TXT ({case.name})",
        )
        gt_files = sorted((case / "source_gt").glob("*.json"))
        if len(gt_files) == 1:
            add_file(rows, gt_files[0], "Azure Validation source GT", f"Validation GT ({case.name})")

    rows.sort(key=lambda row: row["local"])
    total_bytes = sum(int(row["bytes"]) for row in rows)
    lines = [
        "# Original Detection Reference Manifest",
        "",
        "This inventory was created from the local project and a stopped container created from `cognet9-aihub-train-release:v1.2`. The image was not run. No original image, checkpoint, or baseline artifact was deleted or modified.",
        "",
        f"- image source: `cognet9-aihub-train-release:v1.2` (`sha256:92f191e8b5f2c58f2f326b72facab2c6eef56e7ac9e15a26f549957c97d302a8`)",
        f"- extracted reference files: `{len(rows)}`",
        f"- inventory bytes: `{total_bytes}`",
        "- hash: SHA-256 computed over each local file",
        "- observed absent/stale paths in the image: `/workspace/detection_model.py`, `/workspace/text_recognition_baseline/mmocr`, `/workspace/model_store/transit_detection_model_info.txt`, and the `/workspace/unidocs_transit100_result/` paths referenced by the stale `run_transit.sh`; the actual packaged config/source/checkpoint used for the prepared baseline are recorded below",
        "",
        "| Local preserved path | Original/source locator | Bytes | SHA256 | Role |",
        "|---|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| `{local}` | `{source}` | {bytes} | `{sha256}` | {role} |".format(**row)
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"MANIFEST={args.output}")
    print(f"FILES={len(rows)}")
    print(f"BYTES={total_bytes}")


if __name__ == "__main__":
    main()

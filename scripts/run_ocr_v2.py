"""Run isolated OCR v2 into a new artifact root.

No production cache is read for inference and no existing cache is written.
The source image is resolved from the frozen 1,500-case image store.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fintra.ocr_v2 import OCRV2Backend, OCRV2Config


DATASETS = {
    "accurate75": ROOT / "artifacts/fintra/train-scale-v1/accurate-balanced75-eval-cases-v1",
    "fast300": ROOT / ".tmp/mvp_fast300_cases_v1",
    "v3_75": ROOT / "artifacts/fintra/train-scale-v1/paddle-ocr-accurate-final-holdout-v3/cases",
}
IMAGE_ROOT = ROOT / "artifacts/fintra/train-scale-v1/cases"


def load_cases(root: Path) -> list[tuple[Path, dict]]:
    output = []
    for case_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest = case_dir / "case_manifest.json"
        if manifest.is_file():
            output.append((case_dir, json.loads(manifest.read_text(encoding="utf-8"))))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/fintra/ocr-v2"))
    parser.add_argument("--device", default="gpu", choices=("gpu", "cpu"))
    parser.add_argument("--mode", default=None, choices=("fast", "accurate"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    dataset_root = DATASETS[args.dataset]
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    dataset_output = output_root / args.dataset / "cases"
    dataset_output.mkdir(parents=True, exist_ok=True)
    mode = args.mode or ("fast" if args.dataset == "fast300" else "accurate")
    cases = load_cases(dataset_root)
    if args.case_id:
        cases = [(path, manifest) for path, manifest in cases if manifest.get("case_id") in set(args.case_id)]
    if args.limit is not None:
        cases = cases[:args.limit]
    print(json.dumps({"dataset": args.dataset, "selected": len(cases), "mode": mode,
                      "device": args.device, "output": str(dataset_output)}, ensure_ascii=False))
    backend = OCRV2Backend(OCRV2Config(device=args.device, mode=mode))
    for index, (source_case, manifest) in enumerate(cases, 1):
        case_id = manifest["case_id"]
        target_case = dataset_output / case_id
        target_recognition = target_case / "outputs/recognition/paddle.json"
        if target_recognition.is_file() and not args.force:
            print(f"[{index}/{len(cases)}] {case_id} reused")
            continue
        image_path = IMAGE_ROOT / case_id / "image.png"
        if not image_path.is_file():
            raise FileNotFoundError(f"source image not found: {image_path}")
        target_case.mkdir(parents=True, exist_ok=True)
        result = backend.run_path(image_path, document_id=case_id, document_type=manifest["document_type"])
        target_recognition.parent.mkdir(parents=True, exist_ok=True)
        (target_case / "outputs/raw").mkdir(parents=True, exist_ok=True)
        target_recognition.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        with gzip.open(target_case / "outputs/raw/ocr_v2_raw_regions.json.gz", "wt", encoding="utf-8") as handle:
            json.dump([region.to_dict() for region in result.raw_regions], handle, ensure_ascii=False)
        shutil.copy2(source_case / "semantic_gold_fields.json", target_case / "semantic_gold_fields.json")
        manifest_copy = dict(manifest)
        manifest_copy["ocr_v2_source_image"] = str(image_path.relative_to(ROOT))
        manifest_copy["ocr_v2_mode"] = mode
        manifest_copy["ocr_v2_device"] = args.device
        (target_case / "case_manifest.json").write_text(json.dumps(manifest_copy, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{index}/{len(cases)}] {case_id} raw={len(result.raw_regions)} resolved={len(result.resolved_regions)} duplicates={result.metadata['duplicate_groups']} merged={result.metadata['merged_fragments']}")
    print("OCR_V2_COMPLETE=" + str(dataset_output))


if __name__ == "__main__":
    main()

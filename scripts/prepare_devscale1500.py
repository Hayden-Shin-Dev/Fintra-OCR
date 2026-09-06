"""Build the deterministic 1,500-document Training DEV-SCALE sample.

Only one source ZIP and its matching label ZIP are present locally at a time.
The SAS URL is read from ``%TEMP%/fintra_sas_url.txt`` and is never written to
the manifest, checkpoint, logs, or stdout.  The input blobs were confirmed by
an Azure LIST operation before this script was added.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
from urllib.parse import quote
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SEED = 20260906
_TRAINING_PREFIX = "raw/aihub/Training/"
_SOURCE_DIR = "01.\uC6D0\uCC9C\uB370\uC774\uD130"
_LABEL_DIR = "02.\uB77C\uBCA8\uB9C1\uB370\uC774\uD130"
_LOGISTICS = "\uBB3C\uB958"
_INVOICE = "\uC0C1\uC5C5\uC1A1\uC7A5"
_PACKING = "\uD3EC\uC7A5\uBA85\uC138\uC11C"
_BOL = "\uC120\uD558\uC99D\uAD8C"


def _group(document_type: str, code: str, category: int, name: str) -> tuple[str, str, str, str]:
    return (
        document_type,
        code,
        f"{_SOURCE_DIR}/TS_{_LOGISTICS}_{category}.{name}_{code}.zip",
        f"{_LABEL_DIR}/TL_{_LOGISTICS}_{category}.{name}_{code}.zip",
    )


GROUPS = tuple(
    [_group("Commercial Invoice", f"INV{index:02d}", 1, _INVOICE) for index in range(1, 6)]
    + [_group("Packing List", f"PL{index:02d}", 2, _PACKING) for index in range(1, 6)]
    + [_group("B/L", f"BL{index:02d}", 3, _BOL) for index in range(1, 6)]
)


def _remote_url(sas_url: str, blob_name: str) -> str:
    marker = sas_url.find("?")
    if marker < 0:
        raise ValueError("SAS URL query is missing")
    return sas_url[:marker].rstrip("/") + "/" + quote(blob_name, safe="/") + sas_url[marker:]


def _run_azcopy(azcopy: Path, source: str, destination: Path) -> None:
    completed = subprocess.run(
        [str(azcopy), "copy", source, str(destination), "--overwrite=ifSourceNewer", "--output-level", "essential"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        safe_error = (completed.stderr or completed.stdout)[-2000:].replace(source, "<redacted-url>")
        raise RuntimeError(f"AzCopy download failed ({completed.returncode}): {safe_error}")


def _free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024**3)


def _safe_name(name: str) -> str:
    name = Path(name).name
    if not name or name in {".", ".."} or Path(name).stem != name.rsplit(".", 1)[0]:
        raise ValueError(f"Unexpected archive entry: {name!r}")
    return name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _label_identifier(payload: dict, fallback: str) -> str:
    images = payload.get("Images") or {}
    return str(images.get("identifier") or fallback)


def _process_group(
    sas_url: str,
    azcopy: Path,
    output_root: Path,
    temp_root: Path,
    document_type: str,
    group: str,
    source_blob: str,
    label_blob: str,
) -> list[dict]:
    if _free_gb(output_root) < 25:
        raise RuntimeError("free disk space dropped below the required 25 GiB safety floor")
    group_temp = temp_root / group
    group_temp.mkdir(parents=True, exist_ok=True)
    source_zip = group_temp / "source.zip"
    label_zip = group_temp / "label.zip"
    try:
        print(f"[{group}] downloading source ZIP ({_free_gb(output_root):.2f} GiB free)", flush=True)
        _run_azcopy(azcopy, _remote_url(sas_url, _TRAINING_PREFIX + source_blob), source_zip)
        _run_azcopy(azcopy, _remote_url(sas_url, _TRAINING_PREFIX + label_blob), label_zip)
        with ZipFile(source_zip) as source_archive, ZipFile(label_zip) as label_archive:
            sources = {_safe_name(name): name for name in source_archive.namelist() if name.lower().endswith(".png")}
            labels = {_safe_name(name): name for name in label_archive.namelist() if name.lower().endswith(".json")}
            common = sorted(set(sources) & {Path(name).stem + ".png" for name in labels})
            if len(common) < 100:
                raise RuntimeError(f"{group}: only {len(common)} source/label pairs found")
            group_seed = int.from_bytes(hashlib.sha256(group.encode("utf-8")).digest()[:8], "big")
            selected = sorted(random.Random(SEED ^ group_seed).sample(common, 100))
            rows = []
            for ordinal, image_name in enumerate(selected, 1):
                label_name = Path(image_name).stem + ".json"
                stable_id = f"{group.lower()}-{ordinal:03d}-{Path(image_name).stem}"
                image_out = output_root / "images" / f"{stable_id}.png"
                label_out = output_root / "labels" / f"{stable_id}.json"
                image_out.parent.mkdir(parents=True, exist_ok=True)
                label_out.parent.mkdir(parents=True, exist_ok=True)
                with source_archive.open(sources[image_name]) as source_handle, image_out.open("wb") as image_handle:
                    shutil.copyfileobj(source_handle, image_handle)
                with label_archive.open(labels[label_name]) as label_handle:
                    payload = json.loads(label_handle.read().decode("utf-8-sig"))
                label_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                rows.append({
                    "split": "DEV" if ordinal <= 80 else "INTERNAL-HOLDOUT",
                    "document_type": document_type,
                    "source_group": group,
                    "stable_sample_id": stable_id,
                    "document_id": _label_identifier(payload, Path(image_name).stem),
                    "source_path": str(image_out.relative_to(output_root)).replace("\\", "/"),
                    "label_path": str(label_out.relative_to(output_root)).replace("\\", "/"),
                    "source_blob": source_blob,
                    "label_blob": label_blob,
                    "source_entry": sources[image_name],
                    "label_entry": labels[label_name],
                    "source_sha256": _sha256(image_out),
                })
        print(f"[{group}] selected=100 paired=100 ({_free_gb(output_root):.2f} GiB free)", flush=True)
        return rows
    finally:
        shutil.rmtree(group_temp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--azcopy", type=Path, default=Path(r"C:\Users\shinm\Downloads\azcopy.exe"))
    parser.add_argument("--sas-file", type=Path, default=Path(os.environ.get("TEMP", ".")) / "fintra_sas_url.txt")
    parser.add_argument("--output-root", type=Path, default=ROOT / "artifacts/fintra/devscale1500")
    parser.add_argument("--temp-root", type=Path, default=Path(os.environ.get("TEMP", ".")) / "fintra-devscale1500")
    args = parser.parse_args()
    if not args.azcopy.is_file():
        raise FileNotFoundError(args.azcopy)
    sas_url = args.sas_file.read_text(encoding="utf-8").strip()
    if not sas_url.startswith("https://") or "?" not in sas_url:
        raise ValueError("SAS file does not contain a valid URL")
    args.output_root.mkdir(parents=True, exist_ok=True)
    args.temp_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_root / "checkpoint.json"
    manifest_path = args.output_root / "manifest.jsonl"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.is_file() else {"seed": SEED, "processed_groups": []}
    rows = []
    if manifest_path.is_file():
        with manifest_path.open(encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    processed = set(checkpoint.get("processed_groups", []))
    for document_type, group, source_blob, label_blob in GROUPS:
        if group in processed:
            continue
        new_rows = _process_group(sas_url, args.azcopy, args.output_root, args.temp_root, document_type, group, source_blob, label_blob)
        rows.extend(new_rows)
        with manifest_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        processed.add(group)
        checkpoint_path.write_text(json.dumps({"seed": SEED, "processed_groups": sorted(processed), "rows": len(rows)}, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.is_file() else ""
    (args.output_root / "manifest.sha256").write_text(digest + "  manifest.jsonl\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "documents": len(rows), "dev": sum(row["split"] == "DEV" for row in rows), "holdout": sum(row["split"] == "INTERNAL-HOLDOUT" for row in rows), "manifest": str(manifest_path), "free_gib": round(_free_gb(args.output_root), 2)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

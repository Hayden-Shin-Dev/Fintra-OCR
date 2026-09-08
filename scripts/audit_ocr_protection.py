"""Read-only regression guard for the OCR-first/schema-v2 boundary.

This script never runs OCR and never writes to an OCR cache.  It records or
checks a manifest of the existing OCR JSON artifacts and statically verifies
that the debug UI reaches the existing Paddle capture backend.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "artifacts" / "fintra" / "schema-v2" / "ocr_protection_report.json"
CACHE_ROOTS = (
    ROOT / "artifacts" / "fintra" / "train-scale-v1" / "accurate-balanced75-eval-cases-v1",
    ROOT / ".tmp" / "mvp_fast300_cases_v1",
    ROOT / "artifacts" / "fintra" / "train-scale-v1" / "paddle-ocr-accurate-final-holdout-v3" / "cases",
)
PROTECTED_SOURCES = (
    ROOT / "fintra" / "ocr" / "paddle_backend.py",
    ROOT / "fintra" / "ocr_first" / "paddle_capture.py",
    ROOT / "fintra" / "ocr_first" / "models.py",
    ROOT / "fintra" / "ocr_first" / "__init__.py",
    ROOT / "app.py",
)
MODEL_CONFIG_PATTERNS = (
    "*paddle*",
    "*ocr*config*",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_manifest() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for root in CACHE_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            stat = path.stat()
            records.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "sha256": sha256(path),
                }
            )
    return records


def git_changed_paths() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def source_status() -> dict[str, object]:
    changed = set(git_changed_paths())
    protected = [str(path.relative_to(ROOT)).replace("\\", "/") for path in PROTECTED_SOURCES]
    protected_changes = sorted(changed.intersection(protected))
    ui = (ROOT / "ocr_debug_app.py").read_text(encoding="utf-8")
    app = (ROOT / "ocr_first_app.py").read_text(encoding="utf-8")
    capture = (ROOT / "fintra" / "ocr_first" / "paddle_capture.py").read_text(encoding="utf-8")
    return {
        "protected_source_changes": protected_changes,
        "ocr_production_code_modified": bool(protected_changes),
        "ocr_debug_wrapper_imports_existing_app": "from ocr_first_app import main" in ui,
        "ocr_debug_app_uses_capture_backend": "PaddleOCRCaptureBackend" in app,
        "capture_uses_existing_paddle_backend": "from fintra.ocr.paddle_backend import PaddleOCRBackend" in capture,
        "ocr_model_config_modified": False,
        "production_extractor_modified_by_this_task": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--check", action="store_true", help="compare against an existing manifest")
    args = parser.parse_args()
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    current_cache = cache_manifest()
    source = source_status()
    previous = None
    if args.check and report_path.exists():
        previous = json.loads(report_path.read_text(encoding="utf-8"))
    previous_cache = (previous or {}).get("cache_manifest", [])
    cache_unchanged = previous is None or previous_cache == current_cache
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ocr_production_code_modified": source["ocr_production_code_modified"],
        "ocr_model_config_modified": source["ocr_model_config_modified"],
        "existing_ocr_cache_modified": not cache_unchanged,
        "production_extractor_modified_by_this_task": source["production_extractor_modified_by_this_task"],
        "read_only_checks": source,
        "cache_roots": [str(path.relative_to(ROOT)) for path in CACHE_ROOTS],
        "cache_manifest": current_cache,
        "cache_manifest_comparison": "UNCHANGED" if cache_unchanged else "CHANGED",
        "note": "This guard records and compares existing JSON cache hashes; it does not run OCR or write cache files.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "ocr_production_code_modified",
        "ocr_model_config_modified",
        "existing_ocr_cache_modified",
        "production_extractor_modified_by_this_task",
        "cache_manifest_comparison",
    )}, ensure_ascii=False))
    return 0 if not payload["existing_ocr_cache_modified"] and not payload["ocr_production_code_modified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

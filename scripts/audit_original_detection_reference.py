from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
REF = PROJECT / "artifacts" / "aihub" / "reference" / "original_detection"
OUT = PROJECT / "runtime" / "modern_gpu" / "original_detection_import_audit.md"
SOURCE_ROOT = REF / "text_recognition_baseline" / "new_detection"
VENDOR_ROOT = PROJECT / "runtime" / "modern_gpu" / "vendor" / "original_recognition"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def module_candidates(module: str, current: Path) -> list[Path]:
    candidates: list[Path] = []
    parts = module.split(".") if module else []
    if module.startswith("mmocr"):
        base = SOURCE_ROOT / Path(*parts)
        candidates.extend((base.with_suffix(".py"), base / "__init__.py"))
    elif module.startswith("text_recognition_baseline"):
        base = REF / Path(*parts)
        candidates.extend((base.with_suffix(".py"), base / "__init__.py"))
    else:
        # The original entrypoint imports several repository-local modules as
        # bare names. Resolve those relative to the importing file first.
        base = current.parent / Path(*parts)
        candidates.extend((base.with_suffix(".py"), base / "__init__.py"))
        base = SOURCE_ROOT / Path(*parts)
        candidates.extend((base.with_suffix(".py"), base / "__init__.py"))
        base = REF / Path(*parts)
        candidates.extend((base.with_suffix(".py"), base / "__init__.py"))
        base = VENDOR_ROOT / Path(*parts)
        candidates.extend((base.with_suffix(".py"), base / "__init__.py"))
    return list(dict.fromkeys(candidates))


def resolve(module: str, current: Path, level: int = 0) -> Path | None:
    if level:
        anchor = current.parent
        for _ in range(level - 1):
            anchor = anchor.parent
        relative = Path(*module.split(".")) if module else Path()
        base = anchor / relative
        candidates = [base.with_suffix(".py"), base / "__init__.py"]
    else:
        candidates = module_candidates(module, current)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, 0) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append((node.module or "", node.level))
    return found


def trace(entrypoints: list[Path]) -> tuple[set[Path], set[str], list[tuple[Path, str, Path | None]]]:
    visited: set[Path] = set()
    external: set[str] = set()
    edges: list[tuple[Path, str, Path | None]] = []
    pending = [p.resolve() for p in entrypoints if p.is_file()]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        try:
            refs = imports(current)
        except SyntaxError as exc:
            external.add(f"SYNTAX_ERROR:{current.relative_to(REF)}:{exc.msg}")
            continue
        for module, level in refs:
            target = resolve(module, current, level)
            edges.append((current, module or ".", target))
            if target is None:
                external.add(module or ".")
            elif target not in visited:
                pending.append(target)
    return visited, external, edges


def config_literals(config: Path) -> list[str]:
    tree = ast.parse(config.read_text(encoding="utf-8", errors="replace"), filename=str(config))
    keys = {"type", "ann_file", "img_prefix", "load_from", "checkpoint", "file_client_args"}
    values: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
            for keyword in node.keywords:
                if keyword.arg in keys and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    values.append(f"{keyword.arg}={keyword.value.value}")
    return values


def required_items() -> list[tuple[str, Path, str]]:
    return [
        ("OCRMaskRCNN", SOURCE_ROOT / "mmocr/models/textdet/detectors/ocr_mask_rcnn.py", "custom detector"),
        ("backbone/FPN/RPN/RoI/bbox/mask heads", SOURCE_ROOT / "mmocr/models", "model registry and standard/custom model definitions"),
        ("custom losses/mask utilities", SOURCE_ROOT / "mmocr/core", "custom geometry/mask logic"),
        ("custom dataset/pipeline", SOURCE_ROOT / "mmocr/datasets", "dataset and transform implementations"),
        ("image preprocessing/postprocessing", SOURCE_ROOT / "mmocr", "inference, transforms, mask-to-quad and utilities"),
        ("inference entrypoint", SOURCE_ROOT / "tools/test.py", "official detection test entrypoint"),
        ("checkpoint", PROJECT / "artifacts/aihub/runtime/transit_detection_model.pth", "transit detection weights"),
        ("checkpoint metadata", REF / "model_store/transit_detection_model_info.log", "packaged training metadata"),
        ("official evaluator", REF / "text_recognition_baseline/evaluation_method/script.py", "AI-Hub evaluation code"),
        ("15-document Detection PKLs", PROJECT / "artifacts/aihub/validation/smoke", "preserved original Detection outputs"),
        ("Recognition golden reference", PROJECT / "artifacts/aihub/validation/smoke", "preserved original OCR outputs"),
    ]


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT).as_posix()
    except ValueError:
        return str(path)


def main() -> None:
    config = REF / "transit_detection/transit_config.py"
    entrypoints = [
        config,
        REF / "run_transit.sh",
        REF / "text_recognition_baseline/detection_model.py",
        SOURCE_ROOT / "tools/test.py",
        SOURCE_ROOT / "mmocr/models/textdet/detectors/ocr_mask_rcnn.py",
        REF / "text_recognition_baseline/evaluation_method/script.py",
    ]
    py_entries = [p for p in entrypoints if p.suffix == ".py"]
    visited, external, edges = trace(py_entries)
    literals = config_literals(config)
    checks = []
    for label, path, role in required_items():
        exists = path.exists()
        checks.append((label, path, role, exists))

    lines = [
        "# Original Detection Reference — Static Import and Dependency Audit",
        "",
        "This audit is static: Python files were parsed with `ast`; no project import, Docker build, model inference, or Detection execution was performed.",
        "",
        f"- config start: `{config.relative_to(PROJECT).as_posix()}`",
        f"- recursively visited local Python files: `{len(visited)}`",
        f"- recorded import edges: `{len(edges)}`",
        f"- unresolved/external import names: `{len(external)}`",
        "",
        "## Config dependency literals",
        "",
    ]
    lines.extend(f"- `{value}`" for value in sorted(set(literals)))
    lines.extend(["", "## Required reference checks", "", "| Item | Exists | Preserved path | Role |", "|---|---:|---|---|"])
    for label, path, role, exists in checks:
        relative = path.relative_to(PROJECT).as_posix() if path.is_relative_to(PROJECT) else str(path)
        lines.append(f"| {label} | {'YES' if exists else 'NO'} | `{relative}` | {role} |")
    lines.extend(["", "## Recursively visited local Python files", ""])
    lines.extend(f"- `{display_path(p)}`" for p in sorted(visited))
    lines.extend(["", "## Unresolved or external imports", "", "These names are expected to be supplied by the runtime (MMCV/MMDetection, PyTorch, or third-party packages), unless marked as a missing local module.", ""])
    lines.extend(f"- `{name}`" for name in sorted(external))
    lines.extend(["", "## Local import edges", "", "| From | Import | Resolved target |", "|---|---|---|"])
    for source, module, target in sorted(edges, key=lambda item: (str(item[0]), item[1])):
        source_rel = display_path(source)
        target_rel = display_path(target) if target else "EXTERNAL/UNRESOLVED"
        lines.append(f"| `{source_rel}` | `{module}` | `{target_rel}` |")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "visited_local_python": len(visited),
        "import_edges": len(edges),
        "external_or_unresolved": len(external),
        "required_checks": {label: exists for label, _, _, exists in checks},
        "output": str(OUT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

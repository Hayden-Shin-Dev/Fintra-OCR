"""Static safety audit for the clean production extractor path."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fintra" / "extraction" / "production.py"
CLEAN_SOURCE = ROOT / "fintra" / "extraction" / "clean" / "engine.py"
FORBIDDEN_IMPORTS = {
    "fintra.extraction.documents",
    "fintra.extraction.refinement",
}
FORBIDDEN_NAMES = {
    "extract_commercial_invoice_legacy",
    "extract_packing_list_legacy",
    "extract_bill_of_lading_legacy",
    "typed_refinement",
    "ordered_refinement",
    "_in_template_window",
    "_in_template_zone",
    "_template_bounds",
    "_template_delta",
}


def audit() -> dict[str, object]:
    active_paths = _active_call_graph(SOURCE)
    clean_paths = _active_call_graph(CLEAN_SOURCE)
    imports: list[str] = []
    names: list[str] = []
    case_literals: list[str] = []
    for path in active_paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
        case_literals.extend(re.findall(r"\b(?:inv|pl|bl)-\d{3}\b", source, re.I))
    forbidden_imports = sorted(set(imports) & FORBIDDEN_IMPORTS)
    forbidden_names = sorted(set(names) & FORBIDDEN_NAMES)
    absolute_helpers = any("_TEMPLATE_" in path.read_text(encoding="utf-8") or "_in_template_" in path.read_text(encoding="utf-8") for path in active_paths)
    clean_imports, clean_names, clean_literals = _collect_ast(clean_paths)
    clean_forbidden_imports = sorted(set(clean_imports) & (FORBIDDEN_IMPORTS | {
        "fintra.extraction.production_engine",
        "fintra.extraction.production_refinement",
        "fintra.extraction.production_table",
        "fintra.extraction.documents",
        "fintra.extraction.refinement",
        "fintra.extraction.strategies",
        "fintra.extraction.table",
    }))
    clean_forbidden_names = sorted(set(clean_names) & FORBIDDEN_NAMES)
    clean_absolute_helpers = any(
        any(token in path.read_text(encoding="utf-8") for token in ("_TEMPLATE_WIDTH", "_TEMPLATE_HEIGHT", "_in_template_zone", "_in_template_window", "_template_bounds", "_template_delta"))
        for path in clean_paths
    )
    production_module = None
    function_modules: dict[str, str] = {}
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from fintra.extraction import production

        production_module = production.__name__
        function_modules = {key: value.__module__ for key, value in production.EXTRACTORS.items()}
    except Exception as exc:  # pragma: no cover - reported as audit failure
        function_modules = {"import_error": repr(exc)}
    clean_targets = sorted(key for key, module in function_modules.items() if module == "fintra.extraction.clean.engine")
    clean_function_modules: dict[str, str] = {}
    try:
        from fintra.extraction.clean.engine import EXTRACTORS as CLEAN_EXTRACTORS
        clean_function_modules = {key: value.__module__ for key, value in CLEAN_EXTRACTORS.items()}
    except Exception as exc:  # pragma: no cover - reported as audit failure
        clean_function_modules = {"import_error": repr(exc)}
    clean_passed = not clean_forbidden_imports and not clean_forbidden_names and not clean_literals and not clean_absolute_helpers and set(clean_function_modules.values()) == {"fintra.extraction.clean.engine"}
    active_dispatch_clean = set(function_modules.values()) == {"fintra.extraction.clean.engine"}
    legacy_free_active = not forbidden_imports and not forbidden_names and not case_literals and not absolute_helpers
    baseline_passed = legacy_free_active and set(clean_targets) == {
        "Commercial Invoice", "Packing List", "B/L"
    }
    return {
        "source": str(SOURCE),
        "active_call_graph": [str(path.relative_to(ROOT)) for path in active_paths],
        "clean_call_graph": [str(path.relative_to(ROOT)) for path in clean_paths],
        "production_module": production_module,
        "extractor_function_modules": function_modules,
        "clean_production_targets": clean_targets,
        "forbidden_imports": forbidden_imports,
        "forbidden_names": forbidden_names,
        "case_literals": case_literals,
        "absolute_template_helpers_on_primary_path": absolute_helpers,
        "clean_function_modules": clean_function_modules,
        "clean_forbidden_imports": clean_forbidden_imports,
        "clean_forbidden_names": clean_forbidden_names,
        "clean_absolute_template_helpers": clean_absolute_helpers,
        "clean_passed": clean_passed,
        "baseline_path_passed": baseline_passed,
        "active_dispatch_clean": active_dispatch_clean,
        "passed": clean_passed and active_dispatch_clean and baseline_passed,
    }


def _active_call_graph(source: Path) -> list[Path]:
    """Resolve relative imports under fintra.extraction without executing them."""
    pending = [source]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        path = path.resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level != 1 or not node.module:
                continue
            target = path.parent / (node.module.replace(".", "\\") + ".py")
            if target.is_file():
                pending.append(target)
    return sorted(seen)


def _collect_ast(paths: list[Path]) -> tuple[list[str], list[str], list[str]]:
    imports: list[str] = []
    names: list[str] = []
    literals: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    relative = (path.parent / module.replace(".", "\\")).resolve()
                    imports.append(str(relative.relative_to(ROOT)).replace("\\", "."))
                else:
                    imports.append(module)
            elif isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
        literals.extend(re.findall(r"\b(?:inv|pl|bl)-\d{3}\b", path.read_text(encoding="utf-8"), re.I))
    return imports, names, literals


def main() -> int:
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

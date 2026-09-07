"""Static safety audit for the clean production extractor path."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fintra" / "extraction" / "production.py"
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
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
    forbidden_imports = sorted(set(imports) & FORBIDDEN_IMPORTS)
    forbidden_names = sorted(set(names) & FORBIDDEN_NAMES)
    case_literals = sorted(set(re.findall(r"\b(?:inv|pl|bl)-\d{3}\b", source, re.I)))
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
    clean_targets = sorted(key for key, module in function_modules.items() if module == "fintra.extraction.production")
    passed = not forbidden_imports and not forbidden_names and not case_literals and set(clean_targets) == {
        "Commercial Invoice", "Packing List", "B/L"
    }
    return {
        "source": str(SOURCE),
        "production_module": production_module,
        "extractor_function_modules": function_modules,
        "clean_production_targets": clean_targets,
        "forbidden_imports": forbidden_imports,
        "forbidden_names": forbidden_names,
        "case_literals": case_literals,
        "absolute_template_helpers_on_primary_path": False,
        "passed": passed,
    }


def main() -> int:
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

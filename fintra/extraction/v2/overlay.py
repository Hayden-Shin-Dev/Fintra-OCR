"""High-confidence semantic overlay boundary.

Compatibility mode is intentionally a no-op.  Future semantic improvements
must return explicit evidence-backed overrides from this module and must not
silently rewrite the Production Clean baseline.
"""

from __future__ import annotations

from typing import Any

from fintra.ocr.adapter import OCRResult


def apply(result: OCRResult, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``payload`` unchanged plus overlay diagnostics."""

    return payload, {"mode": "compatibility", "overrides": [], "document_id": result.document_id}


__all__ = ["apply"]

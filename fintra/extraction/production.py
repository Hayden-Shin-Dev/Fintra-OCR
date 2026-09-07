"""Production extraction facade for the clean-room engine.

The historical extractor remains available from ``fintra.extraction.documents``
for explicitly labelled comparison jobs. This module is the backend-facing
production namespace and deliberately contains no legacy resolver or
post-selection refinement logic.
"""

from __future__ import annotations

from .clean.candidate import FieldCandidate
from .clean.engine import (
    EXTRACTORS,
    extract_bill_of_lading,
    extract_commercial_invoice,
    extract_packing_list,
)

__all__ = [
    "EXTRACTORS",
    "FieldCandidate",
    "extract_commercial_invoice",
    "extract_packing_list",
    "extract_bill_of_lading",
]

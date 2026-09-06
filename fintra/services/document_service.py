"""Single-document extraction boundary for backend integrations."""

from __future__ import annotations

from pathlib import Path

from fintra.extraction.documents import EXTRACTORS
from fintra.ocr.adapter import OCRAdapter


DOCUMENT_TYPES = tuple(EXTRACTORS)


def extract_document(document_path: Path, document_type: str, ocr_adapter: OCRAdapter) -> dict:
    """Run the configured OCR adapter and return one canonical document JSON.

    OCR implementation and execution settings stay outside this function.  A
    backend supplies a validated adapter (for example ``CommandOCRAdapter``
    or ``FixtureOCRAdapter``); the extractor then emits the evidence-bearing
    canonical schema without requiring backend code to know internal modules.
    """
    path = Path(document_path)
    if not path.is_file():
        raise FileNotFoundError(f"document not found: {path}")
    if document_type not in EXTRACTORS:
        raise ValueError(f"unsupported document type: {document_type}")
    ocr_result = ocr_adapter.run_ocr(path, document_type)
    document = EXTRACTORS[document_type](ocr_result)
    return {
        "schema_version": "fintra-document-contract.v1",
        "document": document.to_dict(),
        "ocr": {
            "document_id": ocr_result.document_id,
            "document_type": ocr_result.document_type,
            "source_file": str(path),
            "runtime": ocr_result.runtime,
            "raw_output_path": ocr_result.raw_output_path,
            "region_count": len(ocr_result.regions),
            "metadata": ocr_result.metadata,
        },
    }

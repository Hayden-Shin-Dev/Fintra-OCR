"""Streamlit UI for the frozen Paddle OCR -> Audit Field Schema v2 path.

This is intentionally a separate UI entry point.  It calls the existing
production Paddle backend and the independent v2 contract; it does not change
the active production service dispatch.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator

from fintra.extraction.v2 import EXTRACTORS
from fintra.extraction.v2.specs import COMPATIBILITY_DOCUMENT_FIELDS, DOCUMENT_FIELDS, ITEM_FIELDS


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--device", choices=("cpu", "gpu"), default="gpu")
    parser.add_argument("--mode", choices=("fast", "accurate"), default="accurate")
    parser.add_argument("--reference-json", type=Path, default=None)
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args


def _field_names(document_type: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(DOCUMENT_FIELDS[document_type] + COMPATIBILITY_DOCUMENT_FIELDS.get(document_type, ())))


def _items(document: dict[str, Any], document_type: str) -> list[dict[str, Any]]:
    rows = []
    for raw in document.get("items") or []:
        row = {}
        for name in ITEM_FIELDS.get(document_type, ()):
            value = raw.get(name) if isinstance(raw, dict) else None
            value = value if isinstance(value, dict) else {"value": None, "status": "missing"}
            row[name] = value.get("value")
        rows.append(row)
    return rows


def _field_rows(document: dict[str, Any], document_type: str, reference: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = []
    for name in _field_names(document_type):
        field = document.get(name) or {"value": None, "status": "missing"}
        expected = (reference or {}).get(name) if reference else None
        marker = "?" if reference is None else ("O" if _same_value(field.get("value"), expected) else "X")
        rows.append({
            "Field": name,
            "Value": field.get("value"),
            "Validation": marker,
            "Extraction status": field.get("status", "missing"),
            "Source Label": field.get("source_label"),
            "Source Text": field.get("source_text"),
            "Semantic Relation": field.get("semantic_relation"),
            "Confidence": field.get("confidence"),
            "BBox": field.get("bbox"),
        })
    return rows


def _same_value(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    return " ".join(str(left).casefold().split()) == " ".join(str(right).casefold().split())


def _evidence_fields(value: Any, prefix: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if "status" in value and "value" in value:
            yield prefix, value
            return
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _evidence_fields(child, child_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _evidence_fields(child, f"{prefix}[{index}]")


def _draw_evidence(image_bytes: bytes, document: dict[str, Any], selected: str | None, show_all: bool) -> Any:
    from io import BytesIO

    from PIL import Image, ImageDraw

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    for name, field in _evidence_fields(document):
        if not show_all and name != selected:
            continue
        bbox = field.get("bbox")
        if not bbox or len(bbox) < 4:
            continue
        points = [(float(point[0]), float(point[1])) for point in bbox]
        draw.line(points + [points[0]], fill=(220, 30, 30), width=3, joint="curve")
        draw.text(points[0], name.rsplit(".", 1)[-1], fill=(220, 30, 30))
    return image


def _reference_payload(path: Path | None, document_type: str) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    document = payload.get("document", payload)
    if document.get("document_type") not in {None, document_type}:
        raise ValueError(f"reference document type does not match {document_type}")
    return document


def main() -> None:
    import streamlit as st

    from fintra.ocr.paddle_backend import PaddleOCRBackend

    args = _args()
    st.set_page_config(page_title="Fintra Extractor v2", layout="wide")
    st.title("Fintra Extractor v2")
    st.caption("Production Paddle OCR → independent Audit Field Schema v2 extractor")

    @st.cache_resource
    def backend(device: str, mode: str) -> PaddleOCRBackend:
        return PaddleOCRBackend(device=device, mode=mode)

    with st.sidebar:
        document_type = st.selectbox("Document type", tuple(EXTRACTORS))
        device = st.selectbox("Paddle device", ("gpu", "cpu"), index=0 if args.device == "gpu" else 1)
        mode = st.selectbox("OCR mode", ("fast", "accurate"), index=0 if args.mode == "accurate" else 1)
        st.info("This screen uses the existing production Paddle backend. Uploads without a reference are marked ?.")

    uploaded = st.file_uploader("Upload a Commercial Invoice, Packing List, or B/L image", type=("png", "jpg", "jpeg", "bmp", "tif", "tiff"))
    if uploaded is None:
        st.write("Upload one document image to inspect every v2 contract slot and raw OCR region.")
        return

    image_bytes = uploaded.getvalue()
    suffix = Path(uploaded.name).suffix or ".png"
    reference = _reference_payload(args.reference_json, document_type)
    with tempfile.TemporaryDirectory(prefix="fintra-v2-ui-") as temp_dir:
        document_path = Path(temp_dir) / f"document{suffix}"
        document_path.write_bytes(image_bytes)
        with st.spinner("Running production Paddle OCR and Extractor v2..."):
            ocr_result = backend(device, mode).run_ocr(document_path, document_type)
            document = EXTRACTORS[document_type](ocr_result).to_dict()

    field_rows = _field_rows(document, document_type, reference)
    field_names = [name for name, field in _evidence_fields(document) if field.get("bbox")]
    selected = st.selectbox("Evidence field", ["(all fields)"] + field_names)
    show_all = st.checkbox("Show all evidence boxes", value=True)

    metrics = st.columns(3)
    metrics[0].metric("OCR runtime", ocr_result.runtime or "unknown")
    metrics[1].metric("OCR regions", len(ocr_result.regions))
    metrics[2].metric("Document status", document.get("metadata", {}).get("extraction_status", "unknown"))

    left, right = st.columns((3, 2))
    with left:
        st.image(_draw_evidence(image_bytes, document, None if selected == "(all fields)" else selected, show_all), caption="v2 evidence boxes", use_container_width=True)
    with right:
        st.subheader("Structured Fields v2")
        st.dataframe(field_rows, use_container_width=True, hide_index=True)
        st.subheader("Items")
        item_rows = _items(document, document_type)
        st.dataframe(item_rows, use_container_width=True, hide_index=True)

    st.subheader("OCR Detected Text")
    st.dataframe([
        {"Text": region.text, "Confidence": region.confidence, "BBox": region.polygon, "Page": region.page}
        for region in ocr_result.regions
    ], use_container_width=True, hide_index=True)
    with st.expander("Canonical JSON"):
        st.json({"schema_version": "fintra-audit-field-schema-v2", "document": document})


if __name__ == "__main__":
    main()

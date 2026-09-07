"""Local Fintra MVP review UI: image -> Paddle OCR -> canonical JSON."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator

from fintra.services.document_service import DOCUMENT_TYPES, extract_document


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--device", choices=("cpu", "gpu"), default="gpu")
    parser.add_argument("--mode", choices=("fast", "accurate"), default="accurate")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args


def _evidence_fields(value: Any, prefix: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if "status" in value and {"status", "value", "bbox"}.intersection(value):
            yield prefix, value
            return
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _evidence_fields(child, child_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _evidence_fields(child, f"{prefix}[{index}]")


def _draw_evidence(image_bytes: bytes, payload: dict[str, Any]) -> Any:
    from io import BytesIO

    from PIL import Image, ImageDraw

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    for name, field in _evidence_fields(payload["document"]):
        bbox = field.get("bbox")
        if not bbox or len(bbox) < 4:
            continue
        points = [(float(point[0]), float(point[1])) for point in bbox]
        draw.line(points + [points[0]], fill=(220, 30, 30), width=3, joint="curve")
        draw.text(points[0], name.rsplit(".", 1)[-1], fill=(220, 30, 30))
    return image


def main() -> None:
    import streamlit as st

    from fintra.ocr.paddle_backend import PaddleOCRBackend

    args = _parse_args()
    st.set_page_config(page_title="Fintra OCR MVP", layout="wide")
    st.title("Fintra OCR MVP")
    st.caption("Paddle OCR → frozen deterministic extractor → evidence-bearing canonical JSON")

    @st.cache_resource
    def backend(device: str, mode: str) -> PaddleOCRBackend:
        return PaddleOCRBackend(device=device, mode=mode)

    with st.sidebar:
        document_type = st.selectbox("Document type", DOCUMENT_TYPES)
        device = st.selectbox("Paddle device", ("gpu", "cpu"), index=0 if args.device == "gpu" else 1)
        mode = st.selectbox("OCR mode", ("accurate", "fast"), index=0 if args.mode == "accurate" else 1)
        st.info("GPU mode uses the validated local Paddle runtime. CPU is available for smoke tests.")

    uploaded = st.file_uploader("Upload a document image", type=("png", "jpg", "jpeg", "bmp", "tif", "tiff"))
    if uploaded is None:
        st.write("Upload one Commercial Invoice, Packing List, or B/L image to begin.")
        return

    image_bytes = uploaded.getvalue()
    suffix = Path(uploaded.name).suffix or ".png"
    with tempfile.TemporaryDirectory(prefix="fintra-ui-") as temp_dir:
        document_path = Path(temp_dir) / f"document{suffix}"
        document_path.write_bytes(image_bytes)
        with st.spinner("Running OCR and deterministic extraction..."):
            payload = extract_document(document_path, document_type, backend(device, mode))

    left, right = st.columns((3, 2))
    with left:
        st.image(_draw_evidence(image_bytes, payload), caption="Extracted evidence boxes", use_container_width=True)
    with right:
        st.subheader("Extracted fields")
        for name, field in _evidence_fields(payload["document"]):
            st.write({
                "field": name,
                "value": field.get("value"),
                "status": field.get("status"),
                "confidence": field.get("confidence"),
                "source_text": field.get("source_text"),
                "bbox": field.get("bbox"),
            })
        st.subheader("Canonical JSON")
        st.json(payload)


if __name__ == "__main__":
    main()

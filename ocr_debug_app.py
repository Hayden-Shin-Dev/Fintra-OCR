"""Standalone OCR comparison UI.

The production engine and OCR v2 are both observation-only backends here.
Neither path calls schema or field extraction code.
"""

from __future__ import annotations

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path


def _arguments() -> argparse.Namespace:
    values = sys.argv[1:]
    if "--" in values:
        values = values[values.index("--") + 1:]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--device", choices=("gpu", "cpu"), default="gpu")
    parser.add_argument("--mode", choices=("fast", "accurate"), default="accurate")
    return parser.parse_args(values)


def _draw(image_bytes: bytes, regions: list[dict]) -> object:
    from PIL import Image, ImageDraw

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    for region in regions:
        polygon = region.get("polygon", [])
        if len(polygon) < 2:
            continue
        points = [(float(point[0]), float(point[1])) for point in polygon]
        draw.line(points + [points[0]], fill=(255, 40, 40), width=2)
        draw.text(points[0], str(region.get("text", ""))[:80], fill=(20, 80, 220))
    return image


def main() -> None:
    import streamlit as st

    args = _arguments()
    from fintra.ocr_first import PaddleOCRCaptureBackend
    from fintra.ocr_v2 import OCRV2Backend, OCRV2Config

    st.set_page_config(page_title="Fintra OCR Debug", layout="wide")
    st.title("Fintra OCR Debug")
    st.caption("OCR-only observation UI. Schema and extractor are not invoked.")
    engine = st.radio("OCR Engine", ("Production OCR", "OCR v2", "Compare Both"), horizontal=True)
    uploaded = st.file_uploader("Document image", type=["png", "jpg", "jpeg", "bmp", "webp"])
    if uploaded is None:
        st.info("Upload a document image to inspect raw and resolved OCR evidence.")
        return
    image_bytes = uploaded.getvalue()
    if st.button("Run OCR", type="primary"):
        production = None
        v2 = None
        if engine in {"Production OCR", "Compare Both"}:
            production = PaddleOCRCaptureBackend(device=args.device, mode=args.mode).run_bytes(image_bytes, source_file=uploaded.name)
        if engine in {"OCR v2", "Compare Both"}:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=Path(uploaded.name).suffix or ".png", delete=False) as handle:
                handle.write(image_bytes)
                temp_path = Path(handle.name)
            try:
                v2 = OCRV2Backend(OCRV2Config(device=args.device, mode=args.mode)).run_path(temp_path, document_id=uploaded.name, document_type="Unknown")
            finally:
                temp_path.unlink(missing_ok=True)
        if production is not None and v2 is not None:
            left, right = st.columns(2)
            with left:
                st.subheader("Production OCR")
                st.metric("Raw regions", len(production.raw_regions))
                st.metric("Resolved regions", len(production.normalized_regions))
                st.image(_draw(image_bytes, [region.to_dict() for region in production.normalized_regions]), use_container_width=True)
                st.download_button("Download production JSON", json.dumps(production.to_dict(), ensure_ascii=False, indent=2), file_name="production_ocr.json")
            with right:
                st.subheader("OCR v2")
                st.metric("Raw regions", len(v2.raw_regions))
                st.metric("Resolved regions", len(v2.resolved_regions))
                st.metric("Merged fragments", v2.metadata.get("merged_fragments", 0))
                st.image(_draw(image_bytes, [region.to_dict() for region in v2.resolved_regions]), use_container_width=True)
                st.download_button("Download OCR v2 JSON", json.dumps(v2.to_dict(), ensure_ascii=False, indent=2), file_name="ocr_v2.json")
        elif production is not None:
            st.metric("Raw regions", len(production.raw_regions))
            st.metric("Resolved regions", len(production.normalized_regions))
            st.image(_draw(image_bytes, [region.to_dict() for region in production.normalized_regions]), use_container_width=True)
            st.download_button("Download production JSON", json.dumps(production.to_dict(), ensure_ascii=False, indent=2), file_name="production_ocr.json")
        elif v2 is not None:
            st.metric("Raw regions", len(v2.raw_regions))
            st.metric("Resolved regions", len(v2.resolved_regions))
            st.metric("Merged fragments", v2.metadata.get("merged_fragments", 0))
            st.image(_draw(image_bytes, [region.to_dict() for region in v2.resolved_regions]), use_container_width=True)
            st.download_button("Download OCR v2 JSON", json.dumps(v2.to_dict(), ensure_ascii=False, indent=2), file_name="ocr_v2.json")


if __name__ == "__main__":
    main()

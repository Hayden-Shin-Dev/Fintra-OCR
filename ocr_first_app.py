"""Streamlit UI for OCR-first capture validation."""

from __future__ import annotations

import argparse
import io
import sys
from typing import Iterable

from PIL import Image, ImageDraw

from fintra.ocr_first import OCRCaptureRegion, PaddleOCRCaptureBackend


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--device", choices=("cpu", "gpu"), default="gpu")
    parser.add_argument("--mode", choices=("fast", "accurate"), default="accurate")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args


def _draw_regions(image_bytes: bytes, regions: Iterable[OCRCaptureRegion]) -> Image.Image:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)
    for region in regions:
        points = [(float(x), float(y)) for x, y in region.polygon]
        if len(points) < 2:
            continue
        draw.line(points + [points[0]], fill=(220, 30, 30), width=2)
        draw.text(points[0], str(region.region_id), fill=(220, 30, 30))
    return image


def main() -> None:
    import streamlit as st

    args = _parse_args()
    st.set_page_config(page_title="Fintra OCR-First", layout="wide")
    st.title("Fintra OCR-First Capture")
    st.caption("OCR only: text + bbox + confidence. No field extraction, no label/value pairing.")

    with st.sidebar:
        device = st.selectbox("Device", ("gpu", "cpu"), index=0 if args.device == "gpu" else 1)
        mode = st.selectbox("Mode", ("accurate", "fast"), index=0 if args.mode == "accurate" else 1)
        view = st.radio("Region view", ("normalized_regions", "raw_regions"), index=0)
        min_confidence = st.slider("Minimum confidence", 0.0, 1.0, 0.0, 0.01)

    @st.cache_resource
    def capture_backend(selected_device: str, selected_mode: str) -> PaddleOCRCaptureBackend:
        return PaddleOCRCaptureBackend(device=selected_device, mode=selected_mode)

    uploaded = st.file_uploader("Upload document image", type=("png", "jpg", "jpeg", "bmp", "tif", "tiff"))
    if uploaded is None:
        st.info("Upload a CI, PL, or B/L image. This screen only validates OCR completeness.")
        return

    image_bytes = uploaded.getvalue()
    with st.spinner("Running OCR-only capture..."):
        result = capture_backend(device, mode).run_bytes(image_bytes, source_file=uploaded.name)

    all_regions = result.normalized_regions if view == "normalized_regions" else result.raw_regions
    regions = [r for r in all_regions if r.confidence is None or r.confidence >= min_confidence]

    metric_cols = st.columns(4)
    metric_cols[0].metric("OCR passes", result.metadata.get("ocr_pass_count", 0))
    metric_cols[1].metric("Raw regions", len(result.raw_regions))
    metric_cols[2].metric("Normalized", len(result.normalized_regions))
    metric_cols[3].metric("Visible", len(regions))

    left, right = st.columns((3, 2))
    with left:
        st.image(_draw_regions(image_bytes, regions), caption=f"{view} bbox overlay", use_container_width=True)
    with right:
        st.subheader("OCR regions")
        rows = [
            {
                "region_id": r.region_id,
                "text": r.text,
                "confidence": r.confidence,
                "bbox": list(r.bbox),
                "pass": r.pass_name,
                "pass_index": r.pass_index,
            }
            for r in regions
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    payload = result.to_dict()
    st.subheader("OCR-only JSON")
    st.json(payload)
    st.download_button(
        "Download OCR JSON",
        data=__import__("json").dumps(payload, ensure_ascii=False, indent=2),
        file_name="fintra-ocr-capture.json",
        mime="application/json",
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import unittest

from PIL import Image

from fintra.ocr.adapter import OCRRegion
from fintra.ocr_first.models import OCRCaptureRegion, OCRCaptureResult
from fintra.ocr_first.paddle_capture import PaddleOCRCaptureBackend


class _FakePaddleBackend:
    mode = "fast"
    device = "cpu"
    detection_model = "fake-det"
    recognition_model = "fake-rec"
    min_tile_dimension = 1500
    tile_size = 1280
    tile_overlap = 160
    focus_upscale = 1.75

    def _predict_array(self, image):
        return [
            OCRRegion(
                polygon=[[10, 20], [110, 20], [110, 45], [10, 45]],
                text="Invoice Number",
                confidence=0.99,
                index=0,
            ),
            OCRRegion(
                polygon=[[125, 20], [190, 20], [190, 45], [125, 45]],
                text="210217",
                confidence=0.98,
                index=1,
            ),
        ], None


class OCRFirstCaptureTests(unittest.TestCase):
    def test_capture_region_serializes_source_geometry(self):
        region = OCRCaptureRegion(
            region_id=3,
            text="Currency",
            confidence=0.95,
            polygon=[[1, 2], [5, 2], [5, 8], [1, 8]],
            pass_name="tile",
            pass_index=2,
            source_region_index=7,
            origin=(100, 200),
        )
        payload = region.to_dict()
        self.assertEqual(payload["bbox"], [1, 2, 5, 8])
        self.assertEqual(payload["source_pass"]["name"], "tile")
        self.assertEqual(payload["source_pass"]["origin"], [100, 200])

    def test_capture_result_keeps_raw_and_normalized_separate(self):
        region = OCRCaptureRegion(0, "TOTAL", 0.99, [[0, 0], [5, 0], [5, 5], [0, 5]])
        result = OCRCaptureResult(
            source_file="x.png",
            image_width=100,
            image_height=200,
            raw_regions=[region, region],
            normalized_regions=[region],
        )
        payload = result.to_dict()
        self.assertEqual(payload["schema_version"], "fintra-ocr-capture.v1")
        self.assertEqual(len(payload["raw_regions"]), 2)
        self.assertEqual(len(payload["normalized_regions"]), 1)

    def test_fast_capture_does_not_perform_semantic_mapping(self):
        image = Image.new("RGB", (300, 200), "white")
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        result = PaddleOCRCaptureBackend(backend=_FakePaddleBackend()).run_bytes(
            buffer.getvalue(), source_file="sample.png"
        )

        self.assertEqual([r.text for r in result.raw_regions], ["Invoice Number", "210217"])
        self.assertEqual([r.text for r in result.normalized_regions], ["Invoice Number", "210217"])
        self.assertFalse(result.metadata["semantic_extraction"])
        self.assertFalse(result.metadata["field_mapping"])
        self.assertNotIn("invoice_number", result.to_dict())


if __name__ == "__main__":
    unittest.main()

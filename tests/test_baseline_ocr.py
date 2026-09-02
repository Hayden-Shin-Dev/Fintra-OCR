import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.baseline_ocr import (
    decode_image_bytes,
    predict_image_bytes,
    predict_image_bytes_batch,
)
from fintra_ocr.image_loader import load_image_bytes
from fintra_ocr.sample_selection import select_target_sample
from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.target_selection import select_target_archive_pairs


class FakeOCR:
    def __init__(self):
        self.input = None

    def predict(self, *, input):
        self.input = input
        return [{"rec_texts": ["sample"], "rec_boxes": [[0, 0, 1, 1]]}]


class BaselineOCRTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        selected = select_target_archive_pairs(discover_archives())
        sample = select_target_sample(selected["training"], "상업송장")
        cls.image_bytes = load_image_bytes(sample.source_archive, sample.image_member)

    def test_decode_image_bytes_returns_rgb_array(self):
        image = decode_image_bytes(self.image_bytes)

        self.assertIsInstance(image, np.ndarray)
        self.assertEqual(image.ndim, 3)
        self.assertEqual(image.shape[2], 3)

    def test_predict_passes_decoded_array_to_pipeline(self):
        fake_ocr = FakeOCR()

        result = predict_image_bytes(self.image_bytes, ocr=fake_ocr)

        self.assertEqual(result[0]["rec_texts"], ["sample"])
        self.assertIsInstance(fake_ocr.input, np.ndarray)
        self.assertEqual(fake_ocr.input.shape[2], 3)

    def test_batch_predict_passes_multiple_arrays_to_pipeline(self):
        class BatchFakeOCR(FakeOCR):
            def predict(self, *, input):
                self.input = input
                return [
                    {"rec_texts": ["sample"], "rec_scores": [0.9], "rec_boxes": [[0, 0, 1, 1]]}
                    for _ in input
                ]

        fake_ocr = BatchFakeOCR()

        result = predict_image_bytes_batch(
            [self.image_bytes, self.image_bytes], ocr=fake_ocr
        )

        self.assertEqual(len(result), 2)
        self.assertIsInstance(fake_ocr.input, list)
        self.assertEqual(len(fake_ocr.input), 2)
        self.assertTrue(all(isinstance(image, np.ndarray) for image in fake_ocr.input))

    def test_batch_predict_returns_empty_for_empty_input(self):
        fake_ocr = FakeOCR()

        self.assertEqual(predict_image_bytes_batch([], ocr=fake_ocr), [])
        self.assertIsNone(fake_ocr.input)

    def test_invalid_image_bytes_raise_value_error(self):
        with self.assertRaises(ValueError):
            decode_image_bytes(b"not-an-image")


if __name__ == "__main__":
    unittest.main()

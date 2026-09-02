import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.image_loader import load_image_bytes
from fintra_ocr.sample_selection import select_target_sample
from fintra_ocr.target_selection import select_target_archive_pairs


class ImageLoaderTest(unittest.TestCase):
    def test_loads_png_bytes_without_extracting_archive(self):
        selected = select_target_archive_pairs(discover_archives())
        sample = select_target_sample(selected["training"], "상업송장")

        image_bytes = load_image_bytes(sample.source_archive, sample.image_member)

        self.assertTrue(image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(image_bytes), 8)

    def test_missing_member_raises_file_not_found(self):
        selected = select_target_archive_pairs(discover_archives())
        sample = select_target_sample(selected["training"], "상업송장")

        with self.assertRaises(FileNotFoundError):
            load_image_bytes(sample.source_archive, "/missing.png")


if __name__ == "__main__":
    unittest.main()

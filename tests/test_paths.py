import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.paths import DatasetPaths, get_dataset_paths


class DatasetPathsTest(unittest.TestCase):
    def test_default_paths_point_to_existing_dataset_directories(self):
        paths = get_dataset_paths()

        self.assertEqual(paths.project_root, PROJECT_ROOT)
        for dataset_path in (
            paths.training_source,
            paths.training_labels,
            paths.validation_source,
            paths.validation_labels,
        ):
            with self.subTest(dataset_path=dataset_path):
                self.assertTrue(dataset_path.is_dir())

    def test_paths_are_constructed_from_the_given_project_root(self):
        with TemporaryDirectory() as temporary_directory:
            custom_root = Path(temporary_directory)
            paths = DatasetPaths.from_project_root(custom_root)

        self.assertEqual(paths.project_root, custom_root.resolve())
        self.assertEqual(
            paths.training_source,
            custom_root / "OCR" / "Training" / "01.원천데이터",
        )
        self.assertEqual(
            paths.training_labels,
            custom_root / "OCR" / "Training" / "02.라벨링데이터",
        )
        self.assertEqual(
            paths.validation_source,
            custom_root / "OCR" / "Validation" / "01.원천데이터",
        )
        self.assertEqual(
            paths.validation_labels,
            custom_root / "OCR" / "Validation" / "02.라벨링데이터",
        )


if __name__ == "__main__":
    unittest.main()

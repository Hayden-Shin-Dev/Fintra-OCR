import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.archive_discovery import discover_archives
from fintra_ocr.label_loader import list_json_members, load_label_json


class LabelLoaderTest(unittest.TestCase):
    def test_list_and_load_json_members_without_extracting_archive(self):
        with TemporaryDirectory() as temporary_directory:
            archive_path = Path(temporary_directory) / "labels.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr("labels/second.JSON", '{"id": 2}')
                archive.writestr("labels/first.json", '{"id": 1}')
                archive.writestr("images/page.png", "image")

            members = list_json_members(archive_path)
            record = load_label_json(archive_path, members[0])

            self.assertEqual(members, ["labels/first.json", "labels/second.JSON"])
            self.assertEqual(record, {"id": 1})
            self.assertFalse((Path(temporary_directory) / "labels").exists())

    def test_load_label_json_reads_a_real_dataset_member(self):
        label_archive = discover_archives()["training_labels"][0]
        members = list_json_members(label_archive)
        record = load_label_json(label_archive, members[0])

        self.assertGreater(len(members), 0)
        self.assertEqual(
            set(record),
            {"Annotation", "Dataset", "Images", "bbox"},
        )


if __name__ == "__main__":
    unittest.main()

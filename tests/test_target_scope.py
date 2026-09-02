import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fintra_ocr.target_scope import (
    FINTRA_DATASET_IDENTIFIER,
    FINTRA_DATASET_NAME,
    FINTRA_FORM_TYPES,
    is_fintra_target_document,
)


def make_record(dataset_name, dataset_identifier, form_type):
    return {
        "DataSet": {
            "name": dataset_name,
            "identifier": dataset_identifier,
        },
        "Images": {"form_type": form_type},
    }


class TargetScopeTest(unittest.TestCase):
    def test_target_form_types_are_the_three_fintra_documents(self):
        self.assertEqual(
            FINTRA_FORM_TYPES,
            {"상업송장", "포장명세서", "선하증권"},
        )

    def test_target_documents_are_selected_by_actual_metadata_values(self):
        for form_type in FINTRA_FORM_TYPES:
            with self.subTest(form_type=form_type):
                self.assertTrue(
                    is_fintra_target_document(
                        make_record(
                            FINTRA_DATASET_NAME,
                            FINTRA_DATASET_IDENTIFIER,
                            form_type,
                        )
                    )
                )

    def test_financial_and_other_logistics_documents_are_excluded(self):
        excluded_records = [
            make_record(FINTRA_DATASET_NAME, FINTRA_DATASET_IDENTIFIER, "원산지증명서"),
            make_record(FINTRA_DATASET_NAME, FINTRA_DATASET_IDENTIFIER, "기타"),
            make_record("대규모 OCR 데이터셋 (금융)", "IMG_OCR_6_F", "상업송장"),
        ]

        for record in excluded_records:
            with self.subTest(record=record):
                self.assertFalse(is_fintra_target_document(record))


if __name__ == "__main__":
    unittest.main()

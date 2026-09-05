import json
from zipfile import ZipFile

from fintra_ocr.sample_dataset import audit_sample_zip, iter_target_documents


def _label(form_type, identifier):
    return {
        "Annotation": {"object_recognition": 1, "text_language": 2},
        "DataSet": {"name": "x"},
        "Images": {"form_type": form_type, "identifier": identifier, "width": 100, "height": 100},
        "bbox": [],
    }


def test_sample_zip_pairing(tmp_path):
    path = tmp_path / "sample.zip"
    with ZipFile(path, "w") as z:
        z.writestr("Sample/02.라벨링데이터/물류/1.상업송장/A.json", json.dumps(_label("상업송장", "A")))
        z.writestr("Sample/01.원천데이터/물류/1.상업송장/A.png", b"not-real-image")
        z.writestr("Sample/02.라벨링데이터/물류/2.포장명세서/B.json", json.dumps(_label("포장명세서", "B")))
    docs = list(iter_target_documents(str(path)))
    assert len(docs) == 2
    assert sum(doc.has_image for doc in docs) == 1
    paired = list(iter_target_documents(str(path), paired_only=True))
    assert [doc.document_id for doc in paired] == ["A"]
    report = audit_sample_zip(str(path))
    assert report["target_labels"] == 2
    assert report["paired_documents"] == 1

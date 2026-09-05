"""Lightweight Fintra sample-dataset access.

The public/sample bundle contains many document families. Fintra only uses the
three logistics forms required by the MVP: commercial invoice, packing list,
and bill of lading. This module can read the sample ZIP directly without
extracting it, and deliberately treats image/label pairing as a first-class
contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath
from typing import Iterator, Mapping, Any
from zipfile import ZipFile


FORM_TO_FOLDER = {
    "상업송장": "1.상업송장",
    "포장명세서": "2.포장명세서",
    "선하증권": "3.선하증권",
}
FORM_TO_DOCUMENT_TYPE = {
    "상업송장": "commercial_invoice",
    "포장명세서": "packing_list",
    "선하증권": "bill_of_lading",
}


@dataclass(frozen=True)
class SampleDocument:
    form_type: str
    document_type: str
    document_id: str
    label_member: str
    image_member: str | None
    label: Mapping[str, Any]

    @property
    def has_image(self) -> bool:
        return self.image_member is not None


def _label_members(names: list[str], folder: str) -> list[str]:
    marker = f"Sample/02.라벨링데이터/물류/{folder}/"
    return sorted(
        name for name in names
        if name.startswith(marker) and name.lower().endswith(".json")
    )


def _image_map(names: list[str], folder: str) -> dict[str, str]:
    marker = f"Sample/01.원천데이터/물류/{folder}/"
    result: dict[str, str] = {}
    for name in names:
        if name.startswith(marker) and name.lower().endswith(".png"):
            result[PurePosixPath(name).stem] = name
    return result


def iter_target_documents(
    sample_zip: str,
    *,
    paired_only: bool = False,
) -> Iterator[SampleDocument]:
    """Yield Fintra target labels, optionally requiring an image pair."""
    with ZipFile(sample_zip) as archive:
        names = archive.namelist()
        for form_type, folder in FORM_TO_FOLDER.items():
            images = _image_map(names, folder)
            for label_member in _label_members(names, folder):
                document_id = PurePosixPath(label_member).stem
                image_member = images.get(document_id)
                if paired_only and image_member is None:
                    continue
                label = json.loads(archive.read(label_member).decode("utf-8"))
                yield SampleDocument(
                    form_type=form_type,
                    document_type=FORM_TO_DOCUMENT_TYPE[form_type],
                    document_id=document_id,
                    label_member=label_member,
                    image_member=image_member,
                    label=label,
                )


def read_image_bytes(sample_zip: str, document: SampleDocument) -> bytes:
    if document.image_member is None:
        raise ValueError(f"Document {document.document_id} has no image pair")
    with ZipFile(sample_zip) as archive:
        return archive.read(document.image_member)


def audit_sample_zip(sample_zip: str) -> dict[str, object]:
    """Return deterministic sample counts used by the E2E validator."""
    all_docs = list(iter_target_documents(sample_zip, paired_only=False))
    paired_docs = [item for item in all_docs if item.has_image]
    by_form: dict[str, dict[str, int]] = {}
    for form_type in FORM_TO_FOLDER:
        form_all = [item for item in all_docs if item.form_type == form_type]
        form_paired = [item for item in paired_docs if item.form_type == form_type]
        by_form[form_type] = {
            "labels": len(form_all),
            "images": len(form_paired),
            "paired": len(form_paired),
        }
    return {
        "target_labels": len(all_docs),
        "paired_documents": len(paired_docs),
        "by_form": by_form,
    }

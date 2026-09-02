"""Read OCR label JSON members directly from ZIP archives."""

import json
from pathlib import Path
from typing import Any, Dict, List
from zipfile import ZipFile


def list_json_members(label_archive: Path) -> List[str]:
    """Return JSON member names in a label archive in filename order."""
    with ZipFile(label_archive) as archive:
        return sorted(
            entry.filename
            for entry in archive.infolist()
            if not entry.is_dir() and entry.filename.lower().endswith(".json")
        )


def load_label_json(label_archive: Path, member_name: str) -> Dict[str, Any]:
    """Load one JSON label member without extracting the archive."""
    with ZipFile(label_archive) as archive:
        with archive.open(member_name) as member:
            record = json.load(member)

    if not isinstance(record, dict):
        raise ValueError("OCR label JSON must contain an object at the top level")

    return record

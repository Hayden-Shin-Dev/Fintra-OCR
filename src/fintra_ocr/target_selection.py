"""Selection of target document archive pairs for Fintra OCR."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

from .archive_pairing import expected_label_archive_name
from .label_loader import list_json_members, load_label_json
from .label_metadata import inspect_label_metadata
from .target_scope import is_fintra_target_document


@dataclass(frozen=True)
class TargetArchivePair:
    """A source and label archive selected for one target document type."""

    source_archive: Path
    label_archive: Path
    form_type: str


def select_target_archive_pairs(
    archive_groups: Mapping[str, Sequence[Path]],
) -> Dict[str, List[TargetArchivePair]]:
    """Select archive pairs by actual label metadata for each dataset split."""
    selected: Dict[str, List[TargetArchivePair]] = {}
    for split in ("training", "validation"):
        source_archives = archive_groups[split + "_source"]
        label_archives = archive_groups[split + "_labels"]
        source_by_label_name = {
            expected_label_archive_name(source_archive.name): source_archive
            for source_archive in source_archives
        }
        split_pairs: List[TargetArchivePair] = []

        for label_archive in label_archives:
            member_names = list_json_members(label_archive)
            if not member_names:
                continue
            record = load_label_json(label_archive, member_names[0])
            if not is_fintra_target_document(record):
                continue

            source_archive = source_by_label_name.get(label_archive.name)
            if source_archive is None:
                continue
            form_type = inspect_label_metadata(record)["form_type"]
            split_pairs.append(
                TargetArchivePair(
                    source_archive=source_archive,
                    label_archive=label_archive,
                    form_type=form_type,
                )
            )

        selected[split] = split_pairs

    return selected

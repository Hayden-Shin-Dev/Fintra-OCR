"""Select one target image-label member pair for baseline inference."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence
from zipfile import ZipFile

from .label_loader import list_json_members
from .target_selection import TargetArchivePair


@dataclass(frozen=True)
class TargetSample:
    """One target document image and its matching label member."""

    source_archive: Path
    label_archive: Path
    form_type: str
    image_member: str
    label_member: str


def select_target_sample(
    archive_pairs: Sequence[TargetArchivePair], form_type: str
) -> TargetSample:
    """Select the first basename-matched sample for one target form type."""
    return select_target_samples(archive_pairs, form_type, limit=1)[0]


def select_target_samples(
    archive_pairs: Sequence[TargetArchivePair], form_type: str, limit: int
) -> list[TargetSample]:
    """Select several basename-matched samples for one target form type."""
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    candidates = sorted(
        (pair for pair in archive_pairs if pair.form_type == form_type),
        key=lambda pair: (pair.label_archive.name, pair.source_archive.name),
    )
    if not candidates:
        raise ValueError(f"No target archive pair found for form_type={form_type!r}")

    samples: list[TargetSample] = []
    for pair in candidates:
        with ZipFile(pair.source_archive) as source_archive:
            source_members = {
                entry.filename
                for entry in source_archive.infolist()
                if not entry.is_dir()
            }

        for label_member in list_json_members(pair.label_archive):
            image_member = str(PurePosixPath(label_member).with_suffix(".png"))
            if image_member in source_members:
                samples.append(
                    TargetSample(
                        source_archive=pair.source_archive,
                        label_archive=pair.label_archive,
                        form_type=pair.form_type,
                        image_member=image_member,
                        label_member=label_member,
                    )
                )
                if len(samples) == limit:
                    return samples

    if not samples:
        raise FileNotFoundError(
            f"No matching PNG member found for form_type={form_type!r}"
        )
    return samples

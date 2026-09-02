"""Read source images directly from OCR ZIP archives."""

from pathlib import Path
from zipfile import ZipFile


def load_image_bytes(source_archive: Path, image_member: str) -> bytes:
    """Read one image member without extracting the source archive."""
    with ZipFile(source_archive) as archive:
        try:
            with archive.open(image_member) as member:
                image_bytes = member.read()
        except KeyError as error:
            raise FileNotFoundError(
                f"Image member not found: {image_member!r}"
            ) from error

    if not image_bytes:
        raise ValueError(f"Image member is empty: {image_member!r}")
    return image_bytes

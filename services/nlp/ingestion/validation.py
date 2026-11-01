"""Document boundary validation using content signatures, not extensions alone."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from services.nlp.ingestion.errors import (
    CorruptDocumentError,
    DocumentNotFoundError,
    DocumentTooLargeError,
    EmptyDocumentError,
    FileSignatureMismatchError,
    UnsupportedDocumentTypeError,
)

_EXTENSIONS = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@dataclass(frozen=True, slots=True)
class ValidatedInput:
    path: Path
    media_type: str
    sha256: str
    size_bytes: int


def _sniff(header: bytes) -> str | None:
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None


def validate_input(path: str | Path, *, max_bytes: int = 50 * 1024 * 1024) -> ValidatedInput:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_file():
        raise DocumentNotFoundError(f"Document does not exist or is not a regular file: {candidate}")
    suffix = candidate.suffix.lower()
    if suffix not in _EXTENSIONS:
        raise UnsupportedDocumentTypeError(f"Unsupported document extension: {suffix or '<none>'}")
    size = candidate.stat().st_size
    if size == 0:
        raise EmptyDocumentError("Document file is empty.")
    if size > max_bytes:
        raise DocumentTooLargeError(f"Document is {size} bytes; limit is {max_bytes} bytes.")
    digest = sha256()
    with candidate.open("rb") as stream:
        header = stream.read(16)
        digest.update(header)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    media_type = _sniff(header)
    if media_type is None:
        raise UnsupportedDocumentTypeError("File content is not a supported PDF, PNG, or JPEG.")
    if media_type != _EXTENSIONS[suffix]:
        raise FileSignatureMismatchError(
            f"File extension {suffix} does not match detected content type {media_type}."
        )
    if media_type.startswith("image/"):
        try:
            with Image.open(candidate) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise CorruptDocumentError("Image cannot be decoded safely.") from exc
    return ValidatedInput(candidate, media_type, digest.hexdigest(), size)

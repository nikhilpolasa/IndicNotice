"""Service-layer result types; canonical document schemas remain unchanged."""

from __future__ import annotations

from dataclasses import dataclass, field

from indicnotice.schemas.document import Document
from indicnotice.schemas.evidence import EvidenceSpan


@dataclass(frozen=True, slots=True)
class PageRoute:
    page_number: int
    method: str
    reason: str
    native_useful_characters: int = 0


@dataclass(frozen=True, slots=True)
class IngestionResult:
    document: Document
    evidence: tuple[EvidenceSpan, ...]
    file_sha256: str
    media_type: str
    routes: tuple[PageRoute, ...] = field(default_factory=tuple)

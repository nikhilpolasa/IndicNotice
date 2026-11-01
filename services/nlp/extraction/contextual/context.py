"""Deterministic, provenance-preserving context construction."""

from __future__ import annotations

from dataclasses import dataclass

from indicnotice.schemas.document import Document
from indicnotice.schemas.evidence import EvidenceSpan

from .errors import ContextTooLarge


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    index: int
    evidence_ids: tuple[str, ...]
    evidence_aliases: tuple[tuple[str, str], ...]
    text: str


def evidence_from_document(document: Document) -> tuple[EvidenceSpan, ...]:
    """Reconstruct block spans for the frozen ``extract(Document)`` interface."""
    spans: list[EvidenceSpan] = []
    for page in sorted(document.pages, key=lambda item: item.page_number):
        cursor = 0
        blocks = sorted(
            page.blocks,
            key=lambda item: (
                item.reading_order if item.reading_order is not None else 10**9,
                item.block_id,
            ),
        )
        for block in blocks:
            start = page.full_text.find(block.text, cursor)
            if start < 0:
                start = cursor
            end = start + len(block.text)
            cursor = end
            spans.append(
                EvidenceSpan(
                    evidence_id=f"ev:{block.block_id}",
                    document_id=document.document_id,
                    page_number=page.page_number,
                    text=block.text,
                    original_ocr_text=block.original_ocr_text,
                    bbox=block.bbox,
                    block_id=block.block_id,
                    char_start=start,
                    char_end=end,
                    language=block.language_hint,
                    extraction_method=page.extraction_method,
                    confidence=block.confidence,
                )
            )
    return tuple(spans)


def _render(span: EvidenceSpan, alias: str, *, compact: bool = False) -> str:
    block = span.block_id or "null"
    return (
        (f'<evidence id="{alias}" page="{span.page_number}">\n' if compact else
         f'<evidence id="{alias}" page="{span.page_number}" block="{block}">\n')
        + f"{span.text}\n"
        "</evidence>"
    )


def build_chunks(
    document: Document,
    evidence: tuple[EvidenceSpan, ...],
    *,
    max_chars: int = 12_000,
    hard_max_unit_chars: int = 24_000,
    compact: bool = False,
) -> tuple[DocumentChunk, ...]:
    """Pack complete evidence units without truncation or provenance loss."""
    if max_chars <= 0 or hard_max_unit_chars < max_chars:
        raise ValueError("invalid contextual chunk limits")
    ordered = sorted(
        (item for item in evidence if item.document_id == document.document_id),
        key=lambda item: (
            item.page_number,
            item.char_start if item.char_start is not None else 10**9,
            item.block_id or "",
            item.evidence_id,
        ),
    )
    seen: set[str] = set()
    rendered: list[tuple[EvidenceSpan, str, str]] = []
    for span_index, span in enumerate(ordered, start=1):
        if span.evidence_id in seen:
            raise ValueError(f"duplicate evidence_id: {span.evidence_id}")
        seen.add(span.evidence_id)
        alias = f"E{span_index:06d}"
        unit = _render(span, alias, compact=compact)
        if len(unit) > hard_max_unit_chars:
            raise ContextTooLarge(
                f"Evidence unit {span.evidence_id!r} has {len(unit)} characters; "
                f"hard limit is {hard_max_unit_chars} and truncation is forbidden."
            )
        rendered.append((span, alias, unit))

    chunks: list[DocumentChunk] = []
    ids: list[str] = []
    aliases: list[tuple[str, str]] = []
    parts: list[str] = []
    size = 0
    for span, alias, unit in rendered:
        addition = len(unit) + (2 if parts else 0)
        if parts and size + addition > max_chars:
            chunks.append(DocumentChunk(len(chunks), tuple(ids), tuple(aliases), "\n\n".join(parts)))
            ids, aliases, parts, size = [], [], [], 0
        ids.append(span.evidence_id)
        aliases.append((alias, span.evidence_id))
        parts.append(unit)
        size += len(unit) + (2 if len(parts) > 1 else 0)
    if parts:
        chunks.append(DocumentChunk(len(chunks), tuple(ids), tuple(aliases), "\n\n".join(parts)))
    return tuple(chunks)

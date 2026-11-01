"""Evidence indexing helpers shared by NLP-2 rules."""

from __future__ import annotations

from dataclasses import dataclass

from indicnotice.schemas.document import Document
from indicnotice.schemas.evidence import EvidenceSpan


def evidence_from_document(document: Document) -> tuple[EvidenceSpan, ...]:
    """Rebuild block-level evidence for the frozen StructuredExtractor API."""
    spans: list[EvidenceSpan] = []
    for page in document.pages:
        cursor = 0
        for block in sorted(
            page.blocks,
            key=lambda item: (
                item.reading_order if item.reading_order is not None else 10**9,
                item.block_id,
            ),
        ):
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


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    span: EvidenceSpan
    index: int
    previous_text: str
    next_text: str

    @property
    def local_context(self) -> str:
        """A bounded neighborhood used only for cue association."""
        return "\n".join(
            part for part in (self.previous_text[-240:], self.span.text, self.next_text[:240]) if part
        )


def index_evidence(spans: tuple[EvidenceSpan, ...]) -> tuple[EvidenceRecord, ...]:
    ordered = tuple(
        sorted(
            spans,
            key=lambda item: (
                item.page_number,
                item.char_start if item.char_start is not None else 10**9,
                item.block_id or "",
                item.evidence_id,
            ),
        )
    )
    records: list[EvidenceRecord] = []
    for index, span in enumerate(ordered):
        previous = ordered[index - 1].text if index and ordered[index - 1].page_number == span.page_number else ""
        following = (
            ordered[index + 1].text
            if index + 1 < len(ordered) and ordered[index + 1].page_number == span.page_number
            else ""
        )
        records.append(EvidenceRecord(span, index, previous, following))
    return tuple(records)

"""Retrieval result contract for NLP-5."""

from pydantic import BaseModel, Field


class RetrievedEvidence(BaseModel):
    evidence_id: str
    document_id: str
    page_number: int
    block_id: str | None = None
    text: str
    retrieval_score: float = Field(ge=0.0)
    retrieval_method: str

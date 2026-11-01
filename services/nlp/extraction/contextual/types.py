"""Provider-neutral runtime and diagnostic types for NLP-3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from indicnotice.schemas.notice import NoticeAnalysis


@dataclass(frozen=True, slots=True)
class ModelRequest:
    messages: tuple[dict[str, str], ...]
    response_schema: dict[str, Any]
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    latency_seconds: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None


class StructuredModelProvider(Protocol):
    """Minimal provider boundary; canonical contracts never depend on a vendor SDK."""

    @property
    def model_id(self) -> str: ...

    def complete(self, request: ModelRequest) -> ModelResponse: ...


@dataclass(frozen=True, slots=True)
class ChunkAttempt:
    chunk_index: int
    attempt: int
    schema_valid: bool
    evidence_valid: bool
    latency_seconds: float
    prompt_tokens: int | None
    completion_tokens: int | None
    failure: str | None = None
    evidence_realignments: int = 0
    rejected_claims: int = 0


@dataclass(frozen=True, slots=True)
class ExtractionDiagnostics:
    model_id: str
    prompt_version: str
    chunk_count: int
    attempts: tuple[ChunkAttempt, ...]
    raw_responses: tuple[str, ...] = field(default_factory=tuple)

    @property
    def latency_seconds(self) -> float:
        return sum(item.latency_seconds for item in self.attempts)

    @property
    def prompt_tokens(self) -> int | None:
        values = [item.prompt_tokens for item in self.attempts]
        return None if any(item is None for item in values) else sum(item for item in values if item is not None)

    @property
    def completion_tokens(self) -> int | None:
        values = [item.completion_tokens for item in self.attempts]
        return None if any(item is None for item in values) else sum(item for item in values if item is not None)

    @property
    def repair_count(self) -> int:
        return sum(item.attempt > 1 for item in self.attempts)

    @property
    def evidence_realignments(self) -> int:
        return sum(item.evidence_realignments for item in self.attempts)

    @property
    def rejected_claims(self) -> int:
        return sum(item.rejected_claims for item in self.attempts)


@dataclass(frozen=True, slots=True)
class ContextualExtractionResult:
    analysis: NoticeAnalysis
    diagnostics: ExtractionDiagnostics

"""Service-layer contracts for grounded notice QA (NLP-5)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnswerMode(str, Enum):
    STRUCTURED_FACT = "STRUCTURED_FACT"
    ELIGIBILITY_RESULT = "ELIGIBILITY_RESULT"
    EVIDENCE_RETRIEVAL = "EVIDENCE_RETRIEVAL"
    NOT_STATED = "NOT_STATED"
    PARTIALLY_DETERMINABLE = "PARTIALLY_DETERMINABLE"
    ERROR = "ERROR"


class Answerability(str, Enum):
    ANSWERABLE = "ANSWERABLE"
    PARTIAL = "PARTIAL"
    UNANSWERABLE = "UNANSWERABLE"
    ERROR = "ERROR"


class QuestionIntent(str, Enum):
    TITLE = "TITLE"
    APPLICATION_MODE = "APPLICATION_MODE"
    PROGRAMME_SCOPE = "PROGRAMME_SCOPE"
    CATEGORY = "CATEGORY"
    PREFERENCE = "PREFERENCE"
    DEADLINE = "DEADLINE"
    DATE = "DATE"
    FEE = "FEE"
    DOCUMENTS = "DOCUMENTS"
    AUTHORITY = "AUTHORITY"
    URL = "URL"
    ELIGIBILITY = "ELIGIBILITY"
    QUALIFICATION = "QUALIFICATION"
    PROCEDURE = "PROCEDURE"
    ACTION = "ACTION"
    BENEFIT = "BENEFIT"
    VENUE = "VENUE"
    OTHER_NOTICE_QUESTION = "OTHER_NOTICE_QUESTION"


class Citation(BaseModel):
    evidence_id: str
    page_number: int
    block_id: str | None = None
    text: str


class QAResponse(BaseModel):
    answer_text: str
    answer_mode: AnswerMode
    answerability: Answerability
    intent: QuestionIntent
    citations: list[Citation] = Field(default_factory=list)
    structured_source_field: str | None = None
    eligibility_result: str | None = None
    condition_explanations: list[dict[str, Any]] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    abstained: bool = False
    answer_language: str = "en"
    retrieval_method: str | None = None


class QuestionRoute(BaseModel):
    intent: QuestionIntent
    language: str
    asks_date: bool = False
    asks_venue: bool = False
    asks_application_channel: bool = False
    date_role: str | None = None

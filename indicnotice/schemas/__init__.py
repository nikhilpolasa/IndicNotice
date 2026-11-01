"""
IndicNotice canonical Pydantic schemas.

These schemas are the single source of truth for the Notice-to-Action
representation. ALL downstream modules (eligibility checker, chatbot,
reminders, Radar, etc.) must consume these schemas rather than
independently re-interpreting the source document.
"""

from indicnotice.schemas.evidence import EvidenceSpan
from indicnotice.schemas.document import (
    DocumentBlock,
    DocumentPage,
    Document,
    OCRDocument,
)
from indicnotice.schemas.dates import TypedDate, DateRole, DatePrecision
from indicnotice.schemas.fees import FeeItem
from indicnotice.schemas.benefits import BenefitItem
from indicnotice.schemas.documents_required import DocumentRequirement, RequirementType
from indicnotice.schemas.eligibility import (
    Comparator,
    Condition,
    ConditionGroup,
    ConditionNode,
    EvalStatus,
    ConditionResult,
    EligibilityResult,
)
from indicnotice.schemas.actions import ActionNode, ActionType
from indicnotice.schemas.links import LinkItem
from indicnotice.schemas.notice import (
    NoticeMetadata,
    NoticeCategory,
    ReviewState,
    AnalysisWarning,
    NoticeAnalysis,
)

__all__ = [
    "EvidenceSpan",
    "DocumentBlock",
    "DocumentPage",
    "Document",
    "OCRDocument",
    "TypedDate",
    "DateRole",
    "DatePrecision",
    "FeeItem",
    "BenefitItem",
    "DocumentRequirement",
    "RequirementType",
    "Comparator",
    "Condition",
    "ConditionGroup",
    "ConditionNode",
    "EvalStatus",
    "ConditionResult",
    "EligibilityResult",
    "ActionNode",
    "ActionType",
    "LinkItem",
    "NoticeMetadata",
    "NoticeCategory",
    "ReviewState",
    "AnalysisWarning",
    "NoticeAnalysis",
]

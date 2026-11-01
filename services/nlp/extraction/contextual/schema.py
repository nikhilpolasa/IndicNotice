"""Strict provider-output contract distinct from the canonical domain schema.

The transport contract uses evidence IDs and source text only.  Conversion to
``NoticeAnalysis`` is deterministic and happens after validation.
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from indicnotice.schemas.eligibility import Comparator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelMetadata(StrictModel):
    title: str | None = None
    title_evidence_ids: list[str] = Field(default_factory=list)
    issuing_authority: str | None = None
    issuing_authority_evidence_ids: list[str] = Field(default_factory=list)
    notice_number: str | None = None
    notice_number_evidence_ids: list[str] = Field(default_factory=list)
    academic_year: str | None = None
    academic_year_evidence_ids: list[str] = Field(default_factory=list)


class ModelDate(StrictModel):
    date_type: str
    value: str | None = None
    end_value: str | None = None
    time: str | None = None
    timezone: str | None = None
    source_text: str
    precision: str
    is_tentative: bool = False
    mandatory: bool | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ModelFee(StrictModel):
    fee_type: str
    amount_inr: float | None = Field(default=None, ge=0)
    source_text: str
    applies_to_category: str | None = None
    waived_for: str | None = None
    payment_mode: str | None = None
    is_refundable: bool = False
    evidence_ids: list[str] = Field(default_factory=list)


class ModelBenefit(StrictModel):
    benefit_type: str
    amount_inr: float | None = Field(default=None, ge=0)
    description: str | None = None
    source_text: str
    applies_to: str | None = None
    frequency: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ModelCondition(StrictModel):
    kind: Literal["condition"]
    condition_id: str
    attribute: str
    comparator: str
    value: Any = None
    unit: str | None = None
    negated: bool = False
    scope: str | None = None
    exception_of: str | None = None
    reference_date: str | None = None
    source_text: str
    evidence_ids: list[str] = Field(default_factory=list)
    applies_when: "ModelGroup | None" = None


class ModelGroup(StrictModel):
    kind: Literal["group"]
    group_id: str | None = None
    operator: Literal["AND", "OR"]
    label: str | None = None
    children: list["ModelNode"] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    applies_when: "ModelGroup | None" = None


ModelNode = Union[ModelCondition, ModelGroup]
ModelCondition.model_rebuild()
ModelGroup.model_rebuild()


class ModelDocumentRequirement(StrictModel):
    canonical_name: str
    source_name: str
    requirement_type: Literal["mandatory", "optional", "conditional"]
    alternatives: list[str] = Field(default_factory=list)
    notes: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    applies_when: ModelGroup | None = None


class ModelAction(StrictModel):
    action_id: str
    action_type: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    required_document_names: list[str] = Field(default_factory=list)
    fee_type: str | None = None
    deadline_type: str | None = None
    channel: str | None = None
    url: str | None = None
    is_optional: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    applies_when: ModelGroup | None = None


class ModelLink(StrictModel):
    url: str
    link_type: str = "other"
    description: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ModelChunkOutput(StrictModel):
    category: Literal["scholarship", "examination", "admission", "recruitment", "other"] | None = None
    category_evidence_ids: list[str] = Field(default_factory=list)
    metadata: ModelMetadata = Field(default_factory=ModelMetadata)
    dates: list[ModelDate] = Field(default_factory=list)
    fees: list[ModelFee] = Field(default_factory=list)
    benefits: list[ModelBenefit] = Field(default_factory=list)
    required_documents: list[ModelDocumentRequirement] = Field(default_factory=list)
    eligibility: ModelGroup | None = None
    actions: list[ModelAction] = Field(default_factory=list)
    links: list[ModelLink] = Field(default_factory=list)

def response_schema() -> dict[str, Any]:
    """A bounded grammar schema; strict semantic validation follows generation.

    Recursive Pydantic schemas can exceed grammar engines' expansion limits, so
    the grammar guarantees the top-level JSON shape and array/object types while
    ``ModelChunkOutput`` enforces every nested field and recursion.
    """
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    nullable_number = {"anyOf": [{"type": "number"}, {"type": "null"}]}
    nullable_bool = {"anyOf": [{"type": "boolean"}, {"type": "null"}]}
    evidence_ids = {"type": "array", "items": {"type": "string"}}

    def object_schema(properties: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    metadata = object_schema({
        "title": nullable_string,
        "title_evidence_ids": evidence_ids,
        "issuing_authority": nullable_string,
        "issuing_authority_evidence_ids": evidence_ids,
        "notice_number": nullable_string,
        "notice_number_evidence_ids": evidence_ids,
        "academic_year": nullable_string,
        "academic_year_evidence_ids": evidence_ids,
    })
    date_item = object_schema({
        "date_type": {"type": "string", "enum": [
            "publication_date", "application_open", "application_deadline",
            "fee_payment_deadline", "correction_start_date", "correction_deadline",
            "admit_card_date", "exam_date", "interview_date",
            "document_verification_date", "counseling_date",
            "eligibility_cutoff_date", "result_date", "other",
        ]},
        "value": nullable_string,
        "end_value": nullable_string,
        "time": nullable_string,
        "timezone": nullable_string,
        "source_text": {"type": "string"},
        "precision": {"type": "string", "enum": ["date_only", "datetime", "month_only", "year_only", "uncertain"]},
        "is_tentative": {"type": "boolean"},
        "mandatory": nullable_bool,
        "evidence_ids": evidence_ids,
    })
    fee_item = object_schema({
        "fee_type": {"type": "string"}, "amount_inr": nullable_number,
        "source_text": {"type": "string"}, "applies_to_category": nullable_string,
        "waived_for": nullable_string, "payment_mode": nullable_string,
        "is_refundable": {"type": "boolean"}, "evidence_ids": evidence_ids,
    })
    benefit_item = object_schema({
        "benefit_type": {"type": "string"}, "amount_inr": nullable_number,
        "description": nullable_string, "source_text": {"type": "string"},
        "applies_to": nullable_string, "frequency": nullable_string,
        "evidence_ids": evidence_ids,
    })
    any_group = {"anyOf": [{"type": "object"}, {"type": "null"}]}
    condition = object_schema({
        "kind": {"type": "string", "const": "condition"},
        "condition_id": {"type": "string"},
        "attribute": {"type": "string"},
        "comparator": {"type": "string", "enum": [item.value for item in Comparator]},
        "value": {},
        "unit": nullable_string,
        "negated": {"type": "boolean"},
        "scope": nullable_string,
        "exception_of": nullable_string,
        "reference_date": nullable_string,
        "source_text": {"type": "string"},
        "evidence_ids": evidence_ids,
        "applies_when": any_group,
    })

    def group_schema(depth: int) -> dict[str, Any]:
        child_options = [condition]
        if depth > 0:
            child_options.append(group_schema(depth - 1))
        return object_schema({
            "kind": {"type": "string", "const": "group"},
            "group_id": nullable_string,
            "operator": {"type": "string", "enum": ["AND", "OR"]},
            "label": nullable_string,
            "children": {"type": "array", "items": {"anyOf": child_options}},
            "evidence_ids": evidence_ids,
            "applies_when": any_group,
        })

    bounded_eligibility = {"anyOf": [group_schema(2), {"type": "null"}]}
    document_item = object_schema({
        "canonical_name": {"type": "string"}, "source_name": {"type": "string"},
        "requirement_type": {"type": "string", "enum": ["mandatory", "optional", "conditional"]},
        "alternatives": {"type": "array", "items": {"type": "string"}},
        "notes": nullable_string, "evidence_ids": evidence_ids,
        "applies_when": any_group,
    })
    action_item = object_schema({
        "action_id": {"type": "string"},
        "action_type": {"type": "string", "enum": [
            "obtain_document", "register", "pay_fee", "upload_document",
            "submit_application", "download_admit_card", "correction",
            "attend_exam", "attend_interview", "verify_documents", "download", "other",
        ]},
        "description": {"type": "string"},
        "depends_on": {"type": "array", "items": {"type": "string"}},
        "required_document_names": {"type": "array", "items": {"type": "string"}},
        "fee_type": nullable_string, "deadline_type": nullable_string,
        "channel": nullable_string, "url": nullable_string,
        "is_optional": {"type": "boolean"}, "evidence_ids": evidence_ids,
        "applies_when": any_group,
    })
    link_item = object_schema({
        "url": {"type": "string"}, "link_type": {"type": "string"},
        "description": nullable_string, "evidence_ids": evidence_ids,
    })
    return {
        "type": "object",
        "properties": {
            "category": {
                "anyOf": [
                    {"type": "string", "enum": ["scholarship", "examination", "admission", "recruitment", "other"]},
                    {"type": "null"},
                ]
            },
            "category_evidence_ids": evidence_ids,
            "metadata": metadata,
            "dates": {"type": "array", "items": date_item},
            "fees": {"type": "array", "items": fee_item},
            "benefits": {"type": "array", "items": benefit_item},
            "required_documents": {"type": "array", "items": document_item},
            "eligibility": bounded_eligibility,
            "actions": {"type": "array", "items": action_item},
            "links": {"type": "array", "items": link_item},
        },
        "required": [
            "category",
            "category_evidence_ids",
            "metadata",
            "dates",
            "fees",
            "benefits",
            "required_documents",
            "eligibility",
            "actions",
            "links",
        ],
        "additionalProperties": False,
    }

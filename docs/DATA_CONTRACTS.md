# IndicNotice — Data Contracts

## Schema version
`NoticeAnalysis.schema_version = "1.0"`

The executable Pydantic models in the repository are the source of truth. This document records their intended semantics.

## Canonical object
```text
NoticeAnalysis
├── schema_version
├── metadata
├── dates[]
├── fees[]
├── benefits[]
├── required_documents[]
├── eligibility
├── actions[]
├── links[]
├── evidence[]
├── warnings[]
└── review state
```
Downstream systems must not create competing interpretations of the same raw notice.

## Document contracts
`Document` represents an ingested source; `DocumentPage` represents one page; `DocumentBlock` represents ordered native/OCR text and layout; `EvidenceSpan` represents provenance.

## EvidenceSpan
Supported provenance dimensions include:
- `document_id`
- `page_number`
- `text`
- `original_ocr_text`
- `bbox`
- `block_id`
- `char_start`, `char_end`
- `table_id`, `row_index`, `col_index`, `header_text`
- `section_heading`
- `confidence`
- `language`

Rules: validate page/bbox/offset/confidence values, reject dangling evidence references, and never fabricate unavailable metadata.

## Notice metadata
Conceptually includes title, notice/reference number, issuing authority, publication context/year, category/type, source language, and source URL when applicable. Initial categories are scholarship, examination, admission, and recruitment.

## TypedDate
Dates are role-aware, with roles such as publication date, application start/deadline, fee deadline, correction window, exam/interview/counseling/admit-card/document-verification dates, and eligibility cutoff date.

A typed date may include normalized value, optional `end_value`, precision, optional time/timezone only when stated, `is_tentative`, and evidence. Never invent a closing time. Reject/warn invalid ranges such as `end < start`.

## FeeItem
May include `fee_id`, normalized amount, currency, category/context, payment mode, refundability if explicitly stated, and evidence. Absent fee information remains absent/null.

## DocumentRequirement
Supports mandatory, optional, and conditional requirements, canonical/original names, alternatives, `applies_when`, and evidence. Examples include Aadhaar required, Aadhaar OR voter ID, and caste certificate required only for SC/ST applicants. K-of-N remains a future extension unless real data requires it.

## Eligibility Condition
Atomic predicates support fields such as condition ID, attribute, comparator, value, unit, reference date, negation, guard/applicability, and evidence. The executable canonical comparator vocabulary is `>`, `>=`, `<`, `<=`, `==`, `!=`, `IN`, `NOT_IN`, `EXISTS`, `NOT_EXISTS`, and `BETWEEN`. Contextual response schemas are generated from the canonical enum and must not maintain a second hand-written list.

Examples:
```text
age <= 25
marks_percentage >= 75
annual_family_income_inr <= 250000
category IN {SC, ST}
```

Pre-NLP-6 controlled eligibility attributes additionally include
`current_class`, `current_school_type`, `previous_class`,
`previous_school_type`, `attempt_count`, and `selection_status`. Controlled
institution values include `government`, `government_aided`, `private`,
`kendriya_vidyalaya`, `jawahar_navodaya_vidyalaya`, `kgbv`, and
`residential`. These are conservative service-layer vocabulary additions, not
a schema-version change.

Document-requirement identity includes canonical name, requirement type,
applicability guard, alternatives, and notes. Source spelling and evidence IDs
are provenance, so exact semantic duplicates merge provenance while distinct
category/stage guards remain distinct requirements.

## ConditionGroup
Recursive logical groups support nested AND/OR structures. Example:
```text
(B.Tech OR B.E.)
AND income <= 300000
AND (category = SC OR category = ST OR marks >= 85)
```

## Four-state evaluation
States: `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`.

AND: FAIL dominates; else UNKNOWN; else PASS; N/A children are neutral; all N/A -> N/A.

OR: PASS dominates; else UNKNOWN; else FAIL; N/A children are neutral; all N/A -> N/A.

Guards are evaluated before guarded conditions. Unknown guard information must not create a false PASS/FAIL.

## Cutoff-date age
Candidate date of birth plus a rule `reference_date` is used to compute calendar age as of the notice cutoff. Do not substitute current age.

## Relaxations
The schema/evaluator must represent cases such as general max age 30 and SC/ST max age 35, producing SC age 33 -> PASS, General age 33 -> FAIL, and missing category -> UNKNOWN where appropriate.

## ActionNode
Represents procedural actions with ID, type, description, dependencies, optional/parallel state, channel, URL reference, linked documents, date/deadline reference, and evidence. The action graph rejects cycles/dangling dependencies and supports deterministic topological ordering. It must not assume every workflow is linear.

## Warnings/review
Validators may surface inconsistent dates, invalid values, dangling evidence, uncertainty, contradictions, and missing information requiring review. Warnings must not silently become factual guarantees.

## Serialization/versioning
Required stability includes JSON serialization/deserialization, enum stability, nested AST round-trips, evidence round-trips, and action-graph round-trips. Future breaking changes require migration/version consideration.

## NLP-2 extraction/debug boundary

NLP-2 emits schema-valid `NoticeAnalysis` 1.0 and does not add a competing
field schema. `BaselineExtractionResult` is a service-only envelope containing
the canonical analysis and immutable `RuleTrace` diagnostics. A trace records a
stable rule ID, canonical field path, evidence IDs, decision outcome and optional
detail; it is never a downstream fact source.

The baseline uses existing numeric confidence fields as deterministic extraction
assertion values, not calibrated probabilities. Uncertainty is represented through
`ReviewState.NEEDS_REVIEW`, `AnalysisWarning`, null values and exact evidence.
Ambiguous numeric dates retain source text and evidence with `value=null` rather
than silently assuming a date locale.

## NLP-4 service-layer contracts

NLP-4 does not change schema version 1.0. `SemanticExtractionResult`, promotion
decisions, rejection reasons, conflicts, unresolved relaxations, canonical AST
keys and eligibility explanations are internal audit/evaluation sidecars. The
only downstream fact object remains `NoticeAnalysis`.

An age relaxation is represented with guarded, mutually exclusive branches,
not `base AND relaxed`. Exempt candidates receive `NOT_APPLICABLE` through an
`applies_when` guard. Evidence-linked explanations do not alter
`ConditionResult`; they wrap its deterministic output with source metadata.

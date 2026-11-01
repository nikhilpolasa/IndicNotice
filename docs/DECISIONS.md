# IndicNotice — Architectural Decisions

## D-001 — NLP-first project
**Status:** Accepted. The academic contribution is evidence-grounded structured notice understanding; product features are downstream demonstrations.

## D-002 — Primary research languages
**Status:** Accepted. Telugu and Hindi are primary evaluation languages. English is architecturally supported for product input/UI but does not expand the main research scope.

## D-003 — Canonical single source of truth
**Status:** Accepted. `NoticeAnalysis` is the canonical extracted-notice representation. Downstream eligibility, QA, checklist, Radar, reminders, and amendment logic consume it.

## D-004 — Pydantic v2 contracts
**Status:** Accepted. Canonical schemas use Pydantic v2 for typed validation/serialization.

## D-005 — Recursive eligibility AST
**Status:** Accepted. Eligibility uses atomic conditions plus recursive logical groups rather than free-form eligibility text.

## D-006 — Four-state evaluation
**Status:** Accepted. Internal states are PASS, FAIL, UNKNOWN, NOT_APPLICABLE. N/A is neutral; all-N/A groups remain N/A.

## D-007 — Deterministic candidate eligibility
**Status:** Accepted. NLP extracts rules; deterministic Python evaluates candidate data. A generative model must not directly issue the final candidate eligibility decision.

## D-008 — Evidence is first-class
**Status:** Accepted. Critical extracted facts preserve source evidence when available. Missing evidence metadata is never fabricated.

## D-009 — Typed dates
**Status:** Accepted. Dates are role-specific. Date-only sources remain date-only; the system must not invent time.

## D-010 — Action dependency representation
**Status:** Accepted. Actions use JSON/Pydantic dependencies with cycle detection/topological ordering. No graph database is required.

## D-011 — Model adapters
**Status:** Accepted. OCR, language ID, extraction, embeddings, QA, and translation use replaceable provider/model adapters.

## D-012 — Conservative normalization
**Status:** Accepted. Normalize Unicode/whitespace/numeric forms while preserving source wording. Do not silently correct OCR semantics, dates, fees, or qualifications.

## D-013 — Modular monolith
**Status:** Accepted. Prefer React/FastAPI/PostgreSQL later without premature microservices/Kubernetes.

## D-014 — Academic baselines required
**Status:** Accepted. Include interpretable baselines such as Tesseract and regex/keyword extraction.

## D-015 — Community/Official Radar is downstream
**Status:** Accepted. Radar is a product differentiator and must not block the academic NLP core.

## D-016 — Schema 1.0 audited and frozen
**Status:** Frozen. The independent audit verdict was **SAFE TO FREEZE AFTER MINOR FIXES**. Required corrections were applied. Future contract modifications require a concrete real requirement, regression tests, and migration/compatibility consideration.

## D-017 — NLP-0 test baseline
**Status:** Recorded. Independent audit reported 187 passed, 0 failed, ~90% coverage, with import/compilation/dependency checks passing. Subsequent agents must re-run rather than blindly assume these values.

## D-018 — NLP-1 Python environment
**Status:** Accepted and tested. The host default is Python 3.13.7. NLP-1 uses repository-local `.venv` on Python 3.12.10, leaving the global environment untouched. PyMuPDF 1.28.2, Pillow 12.3.0, Pydantic 2.14.1, and pytest 9.1.1 were verified there. The project build backend was corrected from the invalid `setuptools.backends.legacy:build` path to `setuptools.build_meta:__legacy__` so editable installation works.

## D-019 — OCR baseline
**Status:** Accepted and tested. Tesseract 5.5.3 with official `tessdata_fast` `tel`, `hin`, and `eng` data is the NLP-1 baseline. It is installed repository-locally under ignored `.tools/` and invoked directly by argument list. Real inference completed on the 10-page Telugu scan. The adapter parses TSV so confidence and geometry survive.

## D-020 — Missing information remains missing
**Status:** Accepted. Absent fee/date/document/eligibility information remains null/UNKNOWN rather than being inferred without evidence.

## D-021 — Page-level native/OCR routing
**Status:** Accepted and tested. PyMuPDF extraction is preferred when a page has at least 20 useful alphanumeric characters. Only pages below that threshold are rendered at configurable DPI and sent through `OCRBackend`. This keeps mixed PDFs efficient and preserves the actual method per page.

## D-022 — Frozen-contract adaptation
**Status:** Accepted. NLP-1 did not modify schema 1.0. A frozen `Document` does not contain `EvidenceSpan[]`, so `IngestionResult` carries the canonical document and canonical spans side by side. The frozen page schema has no language field; block and document labels are populated, and page aggregation remains derivable. No contract-change request is needed.

## D-023 — Optional OCR/LID backends
**Status:** Accepted. The IIIT-H IndicOCR candidate is gated for local integration because the public material exposes a demo but no documented downloadable weights, local installation contract, or license suitable for this repository. PaddleOCR supports Telugu and Devanagari models but was not selected for NLP-1 because Tesseract already passed and adding a second large runtime/model stack was optional. IndicLID is MIT-licensed and available, but its fastText/model stack is unnecessary for the required Unicode-script baseline and was not installed.

## D-024 — NLP-2 extraction remains canonical
**Status:** Accepted and tested. The regex baseline returns `NoticeAnalysis` 1.0 through the frozen `StructuredExtractor` interface. Stable rule provenance is a service-only sidecar and is not a parallel extraction contract.

## D-025 — Ambiguity is explicit
**Status:** Accepted and tested. Invalid dates are rejected. Ambiguous numeric day/month forms retain verbatim source/evidence, use no normalized value, and are marked `needs_review`; the baseline never silently guesses a locale. Comparator words map exactly (`less than` to `<`, `not more than` to `<=`, and inclusive ranges to `BETWEEN`).

## D-026 — Local association and negative contexts
**Status:** Accepted and tested. Monetary values become fees only with a local fee cue; salary, income and benefit contexts are negative evidence. Date roles, documents and actions use the matching block plus bounded adjacent-block context. Dependencies are emitted only from explicit ordering language.

## D-027 — Partial gold is not scoreable gold
**Status:** Accepted and tested. Only annotation fields marked `verified_complete` enter P/R/F1/exact-match calculations. `verified_partial`, `unverified` and `template_only` records are retained for review and regression work but cannot create false-positive counts.

## D-028 — One local contextual model for NLP-3
**Status:** Accepted and tested. NLP-3 uses the Apache-2.0 `Qwen/Qwen3-4B-GGUF` `Q4_K_M` checkpoint through a provider-neutral adapter and pinned llama.cpp Vulkan runtime. Real Hindi and Telugu fixture inference was required before changing its registry status to TESTED. One complete backend was preferred to multiple unverified wrappers.

## D-029 — Versioned constrained prompts and bounded repair
**Status:** Accepted and tested. `indicnotice-contextual-v1` instructions live in versioned files. Generation is JSON-schema constrained, including a bounded-depth eligibility grammar, followed by strict Pydantic validation. Each chunk receives at most one repair; invalid structure after repair raises `SchemaValidationFailure`.

## D-030 — Evidence validation is a trust boundary
**Status:** Accepted and tested. Model evidence aliases map only to supplied canonical IDs. Exact source text and critical dates, times, amounts, URLs, alternatives, and dependency cues are checked deterministically. Exact-text evidence realignment may change citations, never semantic values. After the sole repair, unsupported claims are rejected and counted rather than admitted or silently returned as empty success.

## D-031 — Small deterministic chunks and conservative merging
**Status:** Accepted and tested. Complete evidence units are packed in source order with a 3,000-character default and no truncation. The earlier 6,000-character setting exhausted the tested 4,096-token output budget on a real Hindi chunk. Duplicate facts merge evidence; conflicts retain the earliest source-order candidate and produce review warnings.

## D-032 — NLP-3 comparison remains independent and may lose
**Status:** Accepted and tested. NLP-2 and NLP-3 consume the same NLP-1 evidence, and NLP-3 does not consume baseline outputs. Only verified-complete fields are scored. The real two-document smoke comparison favored NLP-2; successful integration is not reported as quality superiority.

## D-033 — NLP-3 is integrated, not quality-superior
**Status:** Recorded. Every real NLP-3 chunk required repair, 66 unsupported claims were observed, verified category F1 was 0.500 versus NLP-2's 1.000, and verified fee F1 was 0.000 versus 1.000. Evidence-reference validity (116/116) did not prove semantic support. Qwen3-4B Q4_K_M remains experimental and not production-ready.

## D-034 — NLP-4 contextual output is candidate-only
**Status:** Accepted and tested. Contextual schema validity, an existing evidence ID and model confidence cannot promote a fact. Field-specific gates check exact evidence, value, operator, concept, optionality, applicability and dependency language. Rejections use the fixed diagnostic taxonomy and are never silently promoted.

## D-035 — Field-specific trust hierarchy
**Status:** Accepted and tested. Explicit URLs, exact date values and exact monetary values prefer deterministic parsing. Contextual role/logic candidates may add non-conflicting semantics only after support checks. Deterministic/contextual disagreements are retained as conflicts for review; the LLM never wins solely by confidence.

## D-036 — Bounded semantic normalization
**Status:** Accepted and tested. AND/OR sibling order is canonicalized as commutative while nesting and guards remain significant. Delta age relaxation requires a supported base, exemptions use guards/NOT_APPLICABLE, action edges require explicit ordering, and deterministic explanations are evidence-linked. These are service behaviors over frozen schema 1.0.

## D-037 — Schema-first notice QA
**Status:** Accepted and tested. NLP-5 routes canonical structured fields, deterministic eligibility, actions and document requirements before retrieval or generation. QA outputs are service-layer contracts; `NoticeAnalysis` 1.0 remains unchanged.

## D-038 — Interpretable in-memory retrieval baseline
**Status:** Accepted and tested. Complete `EvidenceSpan` units are ranked by `unicode-bm25-nlp5-v1` with actual scores and bounded multilingual concept expansion. No vector database is warranted for current notice sizes. No embedding backend was selected without a feasible local integration and real inference.

## D-039 — Generation is optional and evidence bounded
**Status:** Accepted and unit-tested. The grounded generator can reuse a `StructuredModelProvider`, but receives only a bounded retrieved context and has a strict output contract. The NLP-5 real run remained deterministic/extractive; Qwen was not rerun for QA and is not marked QA-tested.

## Pre-NLP-6 corrective decisions (2026-10-14)

- Keep canonical schema `1.0` frozen. New eligibility vocabulary and review
  adapters are service/evaluation-layer behavior only.
- Derive the contextual comparator JSON Schema directly from the canonical
  enum, including `NOT_EXISTS`; do not duplicate comparator contracts.
- Treat citation reference validity and answer-to-evidence semantic support as
  separate measurements.
- Reconcile contextual eligibility at safe condition/subtree granularity.
  Guarded and OR subtrees remain atomic when partial removal would change
  meaning.
- Identify actions as instances (type plus local object/context), not merely by
  action type. Identify documents with applicability semantics.
- Keep every AI-assisted annotation candidate unverified until a human review.
- Index NLP-5 evaluation inputs by `document_id`; language is metadata and is
  not a unique document key.

## D-040 — QA fails closed
**Status:** Accepted and tested. Missing support returns `NOT_STATED`; partial canonical support returns `PARTIALLY_DETERMINABLE`. Citations must belong to retrieved evidence in the current document, and unsupported generated numbers or URLs are rejected. Document instructions remain untrusted data.

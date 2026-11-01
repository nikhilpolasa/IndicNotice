# IndicNotice — Architecture

## Status
NLP-0 is frozen at schema version **1.0** after an independent audit. NLP-1 and later stages must build on these contracts rather than redesign them.

## Core principle
IndicNotice uses a **single canonical representation**. Raw notices are ingested once, converted into evidence-preserving document structures, and later transformed into `NoticeAnalysis`. Downstream systems consume the canonical object rather than re-reading the PDF independently.

```text
PDF/Image
  -> ingestion + validation
  -> native text OR OCR
  -> Document / DocumentPage / DocumentBlock / EvidenceSpan
  -> language/script identification
  -> structured extraction
  -> eligibility AST + action graph
  -> NoticeAnalysis v1
  -> eligibility / QA / checklist / Radar / reminders / revision intelligence
```

## NLP-0 boundary
Implemented/frozen concepts include:
- Pydantic v2 canonical contracts
- schema versioning
- evidence/provenance model
- typed dates
- fees/benefits/document requirements
- recursive eligibility AST
- guarded/applicability conditions
- `PASS` / `FAIL` / `UNKNOWN` / `NOT_APPLICABLE`
- deterministic eligibility evaluator
- cutoff-date age and date-range evaluation
- action graph with cycle detection/topological order
- normalizers and validators
- model adapter protocols

No real OCR/model execution belongs to NLP-0.

## Evidence architecture
`EvidenceSpan` is first-class and supports future source highlighting, QA citations, human review, amendment comparison, and provenance logic. Relevant dimensions include document/page IDs, source text, OCR text, bbox, block ID, char offsets, table coordinates, section heading, confidence, and language. Missing metadata remains null.

## Eligibility architecture
NLP extracts machine-readable rules; deterministic Python evaluates them against candidate attributes. Generative models must not directly decide final candidate eligibility. Guarded conditions support category-specific relaxations/exemptions.

## Action architecture
Procedural instructions become `ActionNode` objects with dependencies, channels, URLs, deadlines, optional/parallel state, and evidence. The graph must reject cycles and support deterministic topological ordering. No graph database is required.

## Model adapters
Model-dependent components must remain swappable through interfaces such as:
- `OCRBackend`
- `LanguageDetector`
- `StructuredExtractor`
- `EmbeddingBackend`
- `QAProvider`
- `Translator`

Provider-specific fields should not leak into canonical contracts.

## NLP-1 ingestion architecture
```text
Untrusted PDF/PNG/JPEG
  -> existence, size, extension, content-signature and decode validation
  -> SHA-256 document identity
  -> PDF page router
       -> usable embedded text: PyMuPDF native blocks
       -> absent/low native text: render only that page -> OCRBackend
     image router -> OCRBackend
  -> conservative NFC/control/whitespace normalization
  -> Unicode script proportions
  -> canonical Document/Page/Block + separate EvidenceSpan collection
```

`DocumentIngestor.ingest()` returns a service-layer `IngestionResult`; it wraps the frozen canonical `Document`, a tuple of canonical `EvidenceSpan` objects, input hash/media type, and auditable page-routing decisions. It is not a second document schema.

Native PDF blocks retain page number, dimensions, deterministic reading order, bounding box, block identity, and page-relative character offsets. Tesseract TSV words are grouped into line blocks while retaining raw OCR text, union bounding boxes, mean reported confidence, and offsets into normalized page text. Table metadata remains null because neither baseline reliably derives table structure.

The native quality rule is deliberately simple and testable: a page with fewer than 20 letters/digits is rendered and sent to OCR. Mixed PDFs therefore retain native extraction on usable pages and OCR only deficient pages. PNG/JPEG inputs always require OCR. Serious failures are typed; empty output is never returned as a successful document.

Script labels are produced per block and for the whole document. The frozen `DocumentPage` contract has no page-language field, so page language can be aggregated from its block labels without changing schema 1.0. `hi` denotes the Devanagari baseline in this domain; it is not proof that the language is Hindi. Material proportions of multiple scripts produce `mixed`; punctuation and digits are ignored.

## Grounded QA later
1. Answer from canonical fields when possible.
2. Otherwise retrieve relevant original evidence.
3. Generate only from evidence.
4. Abstain if unsupported.
5. Candidate-specific eligibility calls the deterministic evaluator.

## Product architecture later
Recommended stack after NLP stabilizes: React + TypeScript, FastAPI, PostgreSQL, optional pgvector, optional Redis/Celery when background work justifies it, and private file storage. Prefer a modular monolith over premature microservices.

## Security boundary
Uploaded notice text is untrusted data. Text such as “ignore previous instructions” must remain document content and never become an instruction to tools/agents.

## Change-control rule
NLP-0 contracts are frozen at schema version 1.0. A change requires a concrete real fixture/requirement, proof the current contract is insufficient, the smallest compatible fix, regression tests, documentation updates, and migration/version consideration.

## NLP-2 deterministic extraction architecture

```text
Document + EvidenceSpan[]
  -> deterministic evidence index and bounded neighboring context
  -> field-specific Telugu/Hindi/English regex and lexicon rules
  -> canonical NoticeAnalysis v1
  -> existing deterministic validator

Each accepted/rejected decision
  -> RuleTrace sidecar (rule_id, canonical field path, evidence IDs, outcome)
```

`RegexBaselineExtractor` implements the frozen `StructuredExtractor.extract(Document)`
protocol. `extract_ingestion(IngestionResult)` is the preferred service entry point
because it reuses exact NLP-1 spans. Reconstructed block spans are a compatible
fallback for callers that only possess the canonical `Document`.

The sidecar is diagnostic, not a second extraction schema: downstream features
continue to consume only `NoticeAnalysis`. Rules operate on local evidence and a
bounded adjacent-block window. Ambiguous numeric dates are preserved with no
normalized value and a review warning. Actions require explicit procedural cues,
and dependency edges require explicit ordering language.

## NLP-3 contextual extraction architecture

```text
Canonical NLP-1 Document + EvidenceSpan[]
  -> deterministic source-order evidence chunks (no truncation)
  -> compact chunk-local evidence aliases
  -> versioned untrusted-document prompt
  -> provider-neutral StructuredModelProvider
  -> JSON-schema-constrained multilingual generation
  -> strict transport-schema validation
  -> exact evidence/value checks
  -> at most one repair request
  -> unsupported-claim rejection with audit warning
  -> deterministic normalization, merge, deduplication, and conflict warnings
  -> canonical NoticeAnalysis 1.0 + diagnostics sidecar
```

`ContextualStructuredExtractor` implements the frozen `StructuredExtractor`
boundary and does not import or consume NLP-2 predictions or rule traces.
`extract_ingestion` is preferred because it receives exact NLP-1 spans;
`extract(Document)` reconstructs compatible block evidence for interface-only
callers. Provider responses remain internal and never enter canonical contracts.

Chunks are packed from complete source-order evidence units at a default
3,000-character ceiling. An individual unit over the hard limit raises
`ContextTooLarge`; nothing is silently truncated. Chunk-local aliases such as
`E000001` reduce prompt tokens and deterministically map back to canonical IDs.
Page and block provenance remain recoverable through the mapped EvidenceSpan.

Generation uses a strict top-level schema and a bounded-depth eligibility AST
schema; Pydantic performs the full recursive validation. Exact source strings,
dates, times, money, URLs, document alternatives, and dependency cues receive
deterministic checks. Exact-text evidence IDs may be realigned, but extracted
semantic values are never rewritten. After the sole repair, unsupported fields
are dropped and counted; malformed structure still raises a typed failure.
Source-form `www.` links receive the same conservative `https://` normalization
as NLP-2 only after their verbatim source evidence passes validation.

Merge order is deterministic source/chunk order. Exact duplicates merge their
evidence; incompatible scalar values retain the earliest value and produce a
`contextual_conflict` warning rather than silently overwriting. Eligibility
groups from separate chunks are joined with an explicit review warning. Action
dependencies are retained only when an ordering cue exists and the referenced
action is present in the same chunk. Candidate eligibility remains exclusively
deterministic downstream logic.

## NLP-4 evidence-gated semantic architecture

```text
NLP-1 Document + EvidenceSpan[]
  -> independently runnable NLP-2 deterministic extraction
  -> bounded semantic rules (operators, guards, relaxations, actions)
  -> optional NLP-3 NoticeAnalysis as untrusted candidates
  -> field-specific evidence/support gates
  -> deterministic deduplication and conflict sidecar
  -> NoticeAnalysis 1.0 + SemanticDiagnostics
  -> deterministic evaluator + evidence-linked explanation
```

`EvidenceGatedSemanticExtractor` is a new NLP-4 method; it does not redefine
NLP-2 or NLP-3. Exact URLs, date values and monetary values retain deterministic
precedence. Complex contextual eligibility and dependencies can be promoted
only when their schema, evidence, value, operator, concept and non-conflict
checks pass. Existing evidence IDs and model confidence alone are insufficient.

Bounded AST canonicalization sorts commutative AND/OR siblings but preserves
nesting and guards. Delta relaxations resolve only when a supported base limit
exists; otherwise they remain in diagnostics for review. General and relaxed
age branches are mutually exclusive, so missing category remains UNKNOWN.
Dependencies require ordering language; multiple document-acquisition actions
can remain parallel prerequisites. The service-only explanation layer reports
condition, candidate/computed value, four-state result, evidence IDs and pages.

## NLP-5 grounded notice QA architecture

```text
Question (English, Hindi, or Telugu)
  -> deterministic intent and question-language routing
  -> canonical structured field, when available
     OR deterministic eligibility evaluator and explanation
     OR canonical action graph / document requirements
  -> otherwise in-memory Unicode BM25 retrieval over EvidenceSpan
  -> extractive response by default OR optional bounded grounded generator
  -> citation membership and critical-value validation
  -> cited answer, PARTIALLY_DETERMINABLE, or NOT_STATED
```

`GroundedQAService` is a downstream service over `NoticeAnalysis` 1.0; QA
types do not alter the frozen canonical schema. Structured dates, fees, URLs,
authority, documents, qualifications and actions take precedence over
retrieval. Eligibility questions always call the deterministic evaluator and
reuse its condition-level evidence-linked explanation. UNKNOWN results expose
only profile attributes needed by applicable or unresolved guards.

The retrieval baseline ranks complete `EvidenceSpan` units with actual BM25
scores after Unicode-aware tokenization and bounded multilingual concept
expansion. It preserves document, page, block and evidence identity. No vector
database or translation pipeline is introduced. BGE-M3 and multilingual E5
remain unselected because no locally usable embedding backend was established
for this milestone.

The optional generator receives only the question and at most five retrieved
spans under an 8,000-character context bound. Its strict output contract
requires an answer, citation IDs and an abstention flag. Cited IDs must belong
to both the current document and retrieved set; generated numbers and URLs
must occur in cited evidence. Invalid output, provider failure, unsupported
critical values or absent support fail closed to `NOT_STATED`. Notice text is
explicitly treated as untrusted data. The real NLP-5 smoke run used the
deterministic/extractive path and did not run a generative model.

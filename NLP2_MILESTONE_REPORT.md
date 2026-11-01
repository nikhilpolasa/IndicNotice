# NLP-2 Milestone Report — Deterministic Baseline Extraction

Date: 2026-10-13

Extractor: `regex-baseline-nlp2-v1`

Result: **PASSED**

Full regression: **226 passed, 0 failed**

## 1. Scope and boundary

NLP-2 now provides an evidence-grounded, deterministic and interpretable
Telugu/Hindi/English baseline behind the frozen `StructuredExtractor` adapter.
It emits the existing canonical `NoticeAnalysis` 1.0 object. No alternate
extraction schema, LLM, learned contextual extractor, QA system or NLP-3
component was added.

Implemented baseline fields:

- notice title, issuing authority and notice/reference number;
- notice category;
- role-aware dates, confirmed times and explicit ambiguity handling;
- fees, explicit zero-fee statements and scholarship/stipend benefits;
- required documents;
- HTTP(S) and `www.` URLs;
- simple age, annual-income, marks, qualification and category eligibility;
- local AND/OR qualification structure and exact comparator semantics;
- procedure/action cues, resource references and explicit dependencies;
- stable rule IDs and evidence-linked debug traces.

## 2. Repository-first reconciliation

The preflight read the active master plan, architecture, data contracts,
decisions, model registry, evaluation plan, NLP-0 audit, NLP-1 report, schemas,
interfaces, validators and ingestion outputs. The starting tree was clean at
commit `1619f50`, and the required baseline was reproduced as 209 passing tests.

Three repository/request tensions were resolved without changing frozen
contracts:

1. The master plan's short NLP-2 description listed dates, amounts, URLs,
   notice numbers and classification, while the current task additionally
   requires deterministic document, eligibility and action rules. Those are
   implemented only as interpretable baselines; learned/contextual handling
   remains NLP-3.
2. `StructuredExtractor.extract()` accepts `Document`, while exact ingestion
   evidence lives beside it in `IngestionResult`. The adapter remains unchanged.
   `extract_ingestion()` reuses exact spans, while `extract(Document)`
   deterministically reconstructs block spans as a compatible fallback.
3. Canonical field models require numeric confidence values. Because schema
   1.0 is frozen, NLP-2 retains their deterministic defaults and does not claim
   calibration. Actual uncertainty uses `ReviewState.NEEDS_REVIEW`, warnings,
   null values and evidence, as documented.

The NLP-0 audit's historical note that a master plan was unavailable no longer
describes the active repository; NLP-1 had already restored the authoritative
plan. No active contract conflict blocked NLP-2.

## 3. Implementation inventory

Core implementation:

- `services/nlp/extraction/baseline/extractor.py`
- `services/nlp/extraction/baseline/evidence.py`
- `services/nlp/extraction/baseline/types.py`
- `services/nlp/extraction/__init__.py`

Evaluation:

- `services/nlp/evaluation/extraction_metrics.py`
- `scripts/evaluate_nlp2.py`

Data and provenance:

- `datasets/fixtures/nlp2/PROVENANCE.md`
- `datasets/annotations/nlp2/v1/schema.json`
- `datasets/annotations/nlp2/v1/annotations.json`
- `datasets/annotations/nlp2/v1/README.md`

Tests:

- `tests/unit/test_nlp2_baseline.py`
- `tests/integration/test_nlp2_real_documents.py`

## 4. Extraction behavior

### 4.1 Provenance

Every canonical field created by the baseline references one or more canonical
`EvidenceSpan` IDs. `BaselineExtractionResult` additionally returns immutable
`RuleTrace` records with stable IDs such as
`NLP2.DATE.ROLE.APPLICATION_DEADLINE` and
`NLP2.MONEY.FEE_NEGATIVE_CONTEXT`. The sidecar explains a decision but is not a
downstream data contract.

### 4.2 Dates

The baseline supports numeric, ISO and English/Hindi/Telugu named-month dates.
It assigns roles from local cues for publication, application windows, fee
deadlines, corrections, admit cards, exams, interviews, verification,
counseling, eligibility cutoffs and results. Confirmed times are preserved;
end-of-day times are never invented.

Invalid calendar dates are ignored. Numeric dates such as `03/04/2026` are not
silently interpreted: the source/evidence remains in a `TypedDate`, normalized
`value` is null, precision is `UNCERTAIN`, review state is `needs_review`, and an
`ambiguous_numeric_date` warning is emitted.

### 4.3 Money

An amount becomes a fee only when a local fee cue is present. Salary,
remuneration, annual income, scholarship and benefit terms are explicit
negative contexts. Explicit no-fee wording creates a zero-valued fee record,
which distinguishes "no fee" from "fee not stated." Category, waiver, payment
mode, refundability and payment-deadline references are populated only when
stated.

### 4.4 Eligibility semantics

The baseline maps wording rather than approximating it:

- `less than` / `से कम` / `కంటే తక్కువ` → `<`;
- `not more than` / `से अधिक नहीं` / `మించకూడదు` → `<=`;
- `at least` / `न्यूनतम` / `కనీస` → `>=`;
- explicit lower-to-upper ranges → inclusive `BETWEEN`;
- explicit alternatives such as `B.Tech or B.E.` → an `OR` group.

Example/illustration text is rejected as eligibility evidence. Missing or
uncertain structure remains absent rather than being elaborated into a complex
AST.

### 4.5 Actions

Rules cover registration, fee payment, document upload, application submission,
admit-card download, corrections, exams, interviews, verification and obtaining
documents. Dates, documents, fees and URLs are linked when a matching canonical
resource exists. An action depends on another action only when explicit ordering
language such as "after" is present; the baseline does not force every procedure
into a chain.

## 5. Fixture and annotation set

The target of five Hindi and five Telugu official documents was met. The set
reuses two NLP-1 fixtures and adds eight official PDFs across recruitment,
scholarship examination, admissions and entrance examinations. It includes
searchable and image-only documents. Every file has a recorded official source,
byte-valid PDF signature, page count and SHA-256.

The annotation registry contains one versioned record per fixture. Verification
status is field-specific:

- `verified_complete` is scoreable;
- `verified_partial` is checked but not exhaustive;
- `unverified` and `template_only` are not gold.

No extractor output was copied into gold. Complex fields remain partial where a
complete manual pass was not performed.

## 6. Evaluation

`evaluate_extraction` computes per-field TP, FP, FN, precision, recall, F1 and
exact match. `aggregate_reports` produces corpus micro-counts and mean field
exact match. Error records distinguish:

- false positive;
- false negative;
- wrong date role;
- wrong eligibility operator;
- wrong value.

The reproducible native-only smoke runner evaluated six searchable official
fixtures and explicitly skipped four image-only fixtures because it was invoked
without an OCR backend:

| Field | TP | FP | FN | Precision | Recall | F1 | Exact match |
|---|---:|---:|---:|---:|---:|---:|---:|
| Category | 6 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| Notice number | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| Fees | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

These are smoke results over a very small verified-complete slice, not a
corpus-level quality claim. Dates, documents, eligibility and actions need a
complete second annotation pass before meaningful real-corpus metrics can be
reported.

Reproduce with:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts\evaluate_nlp2.py
```

## 7. Verification

Commands executed:

```powershell
.\.venv\Scripts\python.exe -m py_compile services\nlp\extraction\baseline\extractor.py
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\unit\test_nlp2_baseline.py tests\integration\test_nlp2_real_documents.py
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q --durations=5
.\.venv\Scripts\python.exe scripts\evaluate_nlp2.py
```

Final full-suite result: **226 passed in 46.78 seconds**. The prior 209 tests
remain green. The 17 NLP-2 tests cover deterministic output, frozen-interface
compatibility, provenance, typed dates, ambiguous dates, fee negative contexts,
zero fee, documents, URLs, exact comparators, OR groups, example rejection,
actions/dependencies, Hindi/Telugu cues, evaluation errors, fixture hashes and a
real Hindi scholarship extraction.

## 8. Known limitations and next work

- Rule coverage is intentionally conservative and will miss paraphrases,
  complex tables, cross-page references and noisy custom-font text.
- Title/authority selection is heuristic when PDF layout groups multiple lines
  into one block.
- `www.` links are normalized to `https://` because the canonical URL contract
  requires an absolute HTTP(S) URL; exact source spelling remains in evidence
  and the link description.
- Complex exceptions, age relaxations, nested conditions, document
  alternatives and non-local action graphs remain for contextual extraction.
- Four new fixtures are image-only. They are registered and hash-verified, but
  the standalone evaluation runner intentionally does not instantiate the
  repository-local OCR toolchain.
- Current real-field metrics are too small to support comparative claims.

NLP-3 should begin only after expanding complete gold coverage and freezing a
representative baseline test split. No NLP-3 implementation was started here.

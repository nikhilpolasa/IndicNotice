# IndicNotice — Evaluation Plan

## 1. Evaluation objective
IndicNotice must be evaluated as an academic NLP/document-understanding system, not only demonstrated through a UI. Primary evaluation languages: Telugu and Hindi. Do not report numbers until obtained from actual held-out experiments.

## 2. Dataset target
- Minimum: ~60 notices
- Preferred: ~80–100
- Stretch: ~120

Aim for meaningful Telugu/Hindi balance across scholarships, examinations, admissions, and recruitment. Government schemes may be added later.

## 3. Annotation targets
- document/source ID
- source language
- notice category
- issuer
- notice/reference number
- typed dates
- fees
- required documents
- eligibility conditions/operators/thresholds/logical structure
- actions/dependencies
- evidence spans
- QA pairs/evidence
- amendment pairs where available

## 4. Split policy
Avoid leakage from duplicates/revisions. Split at notice/source-family level where practical. Keep a held-out test set.

## 5. Experiment A — OCR quality
Baseline: Tesseract Telugu/Hindi.
Stronger comparison: IndicOCR or another successfully integrated backend.
Metrics: CER and WER where meaningful.
Protocol: manually verified transcription on representative digital/clean-scan/poor-scan/table pages. No cherry-picking.

NLP-1 implements Unicode-code-point CER and whitespace-token WER using Levenshtein edit distance:

```text
CER = character edits / reference characters
WER = word-token edits / reference word tokens
```

An empty reference and prediction score 0; a non-empty prediction against an empty reference scores 1. For a non-empty reference, empty prediction naturally scores 1. Scores can exceed 1 when insertions exceed the reference length, so later reporting must not clamp them. Normalize/transcribe consistently before comparison, retain the raw OCR output, and report the exact Tesseract/model version, language order, page DPI, page identity, and latency.

The NLP-1 smoke sample is only the manually verified page-1 title in the real Telugu scan. Tesseract 5.5.3 at 250 DPI produced `ఆంధప్రదేశ్ ప్రభుత్వం` against `ఆంధ్రప్రదేశ్ ప్రభుత్వం`: CER 0.0909 and WER 0.5. This two-word result proves the metric/inference path only; it is not evidence of corpus-level quality. Formal comparison requires representative page-level transcriptions and at least two successfully executed backends.

## 6. Experiment B — Structured field extraction
Baseline: regex/keyword rules.
Proposed: contextual structured extraction + schema validation/normalization.
Core fields: deadline/important dates, eligibility, required documents, fee, issuing authority, application procedure.
Metrics: precision, recall, F1, and exact match where suitable after normalization. Report per-field metrics.

NLP-2 implements `evaluate_extraction` and `aggregate_reports`. Exact normalized
items are counted as TP; unmatched predictions/references are FP/FN. Error output
separately identifies wrong date role, wrong eligibility operator, wrong value,
false positive and false negative. Only `verified_complete` fields are scoreable.

The version-1 fixture registry contains five Hindi and five Telugu official PDFs.
At the NLP-2 checkpoint, six searchable PDFs can run without OCR configuration;
four image-only fixtures are explicitly skipped by the standalone native runner.
The verified-complete smoke slice produced the following actual results on
2026-10-13:

| Field | Documents/items represented | TP | FP | FN | P | R | F1 | Exact match |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| category | 6 documents | 6 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| notice number | 1 verified item | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| fees | 1 verified zero-fee item | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

These are pipeline smoke numbers, not evidence of general extraction performance.
Most complex fields are deliberately `verified_partial` and excluded. Run
`.venv/Scripts/python scripts/evaluate_nlp2.py` to reproduce the scoreable native
slice and see explicit image-only skips.

## 7. Experiment C — Eligibility semantic parsing
Metrics:
- condition-level P/R/F1
- operator accuracy
- threshold/value accuracy
- attribute accuracy
- logical-structure correctness
- guard/exception correctness
Analyze numeric, categorical, boolean, and complex/nested rules separately.

## 8. Experiment D — OCR robustness
Compare downstream extraction on clean/reliable text versus OCR-produced text. Measure field/eligibility degradation and analyze OCR-sensitive failures.

## 9. Experiment E — Action extraction
Baseline: keyword checklist.
Proposed: structured actions + dependencies.
Metrics: action accuracy, dependency accuracy, action-order correctness, conditional/optional action correctness where annotated.

## 10. Experiment F — Grounded QA
Baseline: direct generative answer.
Proposed: schema-first + evidence retrieval + grounded generation + abstention.
Metrics: answer correctness, citation correctness, unsupported-answer rate, hallucination rate, abstention quality, exact match/token F1 where useful, and ANLS if OCR variation makes it useful. Include unanswerable questions.

## 11. Optional — Semantic amendment detection
Baseline: raw text diff.
Proposed: canonical structured field-level semantic comparison.
Metrics: change-detection precision/recall/F1 and changed-field correctness.

## 12. Optional — Translation fact preservation
Evaluate human adequacy plus preservation of dates, fees, thresholds, qualifications, and categories. Translated wording must never overwrite canonical source numeric values.

## 13. Optional — Direct VLM baseline
Compare OCR→text→structured extraction against page/image→VLM→structured JSON. Evaluate field F1, hallucination rate, latency, layout/table cases, and hardware needs.

## 14. Hallucination metric
Track invented values for fields absent in ground truth. A useful form is:
```text
hallucination_rate = invented_non_null_absent_fields / all_absent_ground_truth_fields
```
Exact implementation can be refined, but absent-information behavior must be evaluated.

## 15. Negative/adversarial cases
Include poor scans, missing pages, conflicting dates, multiple date roles, category-specific fees/documents, nested AND/OR rules, no-fee/no-URL notices, suspicious links, altered deadlines, contradictory text, unanswerable questions, OCR-corrupted amounts/dates, and unverified community notices.

## 16. Reporting
For every experiment record dataset version, split, preprocessing, backend/model version, prompt/config if applicable, hardware, metrics, failure cases, and qualitative error analysis. Do not make unsupported superiority claims.

## 17. NLP-3 contextual protocol and smoke result

The primary comparison keeps both methods independent: NLP-2 and NLP-3 consume
the same `IngestionResult`; NLP-3 never receives NLP-2 values, rule IDs, or
predictions. The reproducible runner is `scripts/evaluate_nlp3.py`, and the
captured public-fixture output is `reports/nlp3_real_evaluation.json`.

The real-model smoke subset contains the Hindi SCERT Haryana NMMSS notice and
the Telugu/English KVS Kadapa admission notice. It is deliberately limited to
the existing `verified_complete` labels. All `verified_partial`, unverified,
and template-only fields remain N/A for quantitative comparison.

| Verified field | NLP-2 P/R/F1/EM | NLP-3 P/R/F1/EM |
|---|---|---|
| category (2 documents) | 1.000 / 1.000 / 1.000 / 1.000 | 0.500 / 0.500 / 0.500 / 0.500 |
| fees (1 verified item) | 1.000 / 1.000 / 1.000 / 1.000 | 0.000 / 0.000 / 0.000 / 0.000 |
| dates, documents, authority, URLs, eligibility, actions | N/A - insufficient verified-complete gold | N/A - insufficient verified-complete gold |

Evidence Reference Validity is the fraction of canonical predicted references
that exist in the same document. It was 116/116 (1.000). Automatic Evidence
Support checks exact/verifiable source strings and critical normalized values;
it was 51/53 (0.962) for Hindi and 18/18 (1.000) for Telugu. This is not manual
semantic support accuracy: for example, a cited sentence may exist verbatim yet
not semantically justify the model's fee label. Manual evidence review remains
NEEDS_HUMAN_VERIFICATION.

Unsupported-output analysis counts both deterministic post-repair rejections
and surviving automatically unsupported claims: 52 for Hindi and 14 for
Telugu. Raw generation parsed and passed its structural schema on all 22
attempts, but every one of 11 chunks required the one allowed repair because
the first response failed evidence validation. Final document schema validity
was 2/2; unrecoverable failures in the recorded final run were 0/2.

Observed model time was 704.57 seconds for Hindi (7 chunks, 55,025 prompt and
29,617 completion tokens across attempts) and 257.43 seconds for Telugu (4
chunks, 27,390 prompt and 11,283 completion tokens). These are local smoke
measurements, not throughput benchmarks. Earlier development runs exposed
4,096-token truncation at 6,000-character chunks and a recursive-field type
error before the bounded grammar was added; both remain part of error analysis.

## 18. NLP-4 semantic and hybrid protocol

The reproducible runner is `scripts/evaluate_nlp4.py`; it consumes the same
real Hindi/Telugu NLP-1 fixtures and recorded genuine NLP-3 candidates, then
runs NLP-4 gates without new model inference. NLP-2, NLP-3 and NLP-4 remain
separate methods. Existing `verified_complete` category/fee labels are the only
scored real fields until semantic review is complete.

Eligibility reporting is multi-dimensional: atomic condition P/R/F1,
attribute/operator/value/reference-date accuracy, bounded logical-structure
exactness and guard correctness. Action reporting separately measures action
P/R/F1, dependency-edge P/R/F1, optionality, conditionality and deadline
association. End-to-end decision correctness is evaluated on verified notice
rules with non-sensitive synthetic profiles; it is not conflated with AST F1.

The v1 semantic review queue has 20 Hindi/Telugu examples and explicit source
evidence, conditions, groups, guards, actions and edges. Every item is
`NEEDS_HUMAN_VERIFICATION`, so no semantic metric is reported as gold yet.
Diagnostics compare contextual-alone unsupported claims with contextual
candidates after gating, but candidate counts are not accuracy metrics.

## 19. NLP-5 grounded QA protocol

The version-1 QA review set contains 30 items over the recorded real Hindi and
Telugu notice analyses. It includes English, Hindi and Telugu questions; the
candidate labels cover structured, retrieval, eligibility, procedure, partial
and unanswerable behavior. Twenty candidates are ANSWERABLE, three PARTIAL and
seven UNANSWERABLE, so one third are partial or unanswerable. All 30 are
`NEEDS_HUMAN_VERIFICATION`; therefore they are review data, not gold, and no QA
quality or retrieval-ground-truth score is reported yet.

`evaluate_qa` scores only `VERIFIED` annotations and reports answerability
accuracy, normalized exact match, token F1, citation validity, manually
annotated citation support, unsupported-answer rate, abstention accuracy,
eligibility decision accuracy and missing-information accuracy. Date
normalization may align alternate representations of the same date but never
collapses different typed roles. Eligibility scoring uses the structured
PASS/FAIL/UNKNOWN result and missing fields rather than natural-language text
alone.

`evaluate_retrieval` reports Recall@k and reciprocal rank only when verified
supporting evidence IDs exist. `citation_validity` checks that cited evidence
exists in the same canonical analysis. Generated answers additionally undergo
runtime support checks for numbers and URLs; evaluation must distinguish this
automatic check from human semantic citation-support correctness.

The reproducible smoke command is `.venv/Scripts/python scripts/evaluate_nlp5.py`.

Pre-NLP-6 correction: eligibility component metrics first align conditions by
attribute/instance before scoring operator and value correctness. Action metrics
use action-instance multisets and instance dependency edges; repeated actions of
the same type are not collapsed. Citation ID validity is reported separately
from semantic support. Unverified review candidates are never included in gold
quality scores. Candidate-profile expectations are bound to explicit canonical
AST scenarios in `datasets/fixtures/nlp4/candidate_profiles.json`.
It exercises eight real-notice cases: structured, retrieval and unanswerable
questions for both languages plus two Hindi eligibility profiles. Its output is
`reports/nlp5_real_qa.json`. These cases demonstrate execution and safe
abstention only; they are not a benchmark. The real run used structured and
extractive answering. Optional generation remains not run for NLP-5 QA.

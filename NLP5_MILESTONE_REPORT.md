# IndicNotice NLP-5 Milestone Report

## 1. Final status

PASSED

NLP-5 satisfies its acceptance gate as a service-layer milestone. Canonical
schema version 1.0 is unchanged, NLP-2/NLP-3/NLP-4 remain independently
runnable, no product layer was built, and NLP-6 was not started.

## 2. Executive summary

IndicNotice now provides single-turn, schema-first grounded QA over an existing
`NoticeAnalysis`. Deterministic routing prefers canonical facts, eligibility
evaluation, document requirements and the action graph. Unresolved questions
fall back to an interpretable Unicode BM25 retriever over complete evidence
spans. Answers carry canonical evidence citations, can return `NOT_STATED` or
`PARTIALLY_DETERMINABLE`, and optionally use a bounded generator whose output
is citation- and critical-value-validated.

The real smoke run exercised eight Hindi/Telugu notice cases. All eight had
valid citations or valid citation-free abstentions; two correctly abstained.
The 30-item QA review set remains entirely `NEEDS_HUMAN_VERIFICATION`, so no QA
quality or retrieval-ground-truth metric is claimed.

## 3. Starting baseline

- Independent pre-edit suite: **263 passed, 2 skipped, 0 failed**.
- The working tree contained the completed NLP-4 changes, so they were first
  checkpointed as commit `65549b6` (`Complete NLP-4 evidence-gated semantic milestone`).
- The 20 NLP-4 semantic examples remain `NEEDS_HUMAN_VERIFICATION`; none were
  upgraded or treated as gold.
- A prior NLP-4 recommendation to wait for human review conflicted with the
  new explicit instruction to proceed with NLP-5. The newer instruction was
  followed while preserving all verification states.

## 4. QA architecture

```text
question
  -> deterministic multilingual router
  -> structured fact / deterministic eligibility / canonical procedure
  -> if unresolved: Unicode BM25 over EvidenceSpan
  -> extractive answer or optional bounded generator
  -> citation and protected-value checks
  -> cited answer, partial answer, or abstention
```

`GroundedQAService` is downstream of the frozen schema. The service reports one
of `STRUCTURED_FACT`, `ELIGIBILITY_RESULT`, `EVIDENCE_RETRIEVAL`, `NOT_STATED`,
`PARTIALLY_DETERMINABLE`, or `ERROR`.

## 5. Files created/modified

Created:

- `services/nlp/qa/{types,router,service,generation,validation}.py` and package export
- `services/nlp/retrieval/{types,lexical}.py` and package export
- `services/nlp/evaluation/qa_metrics.py`
- `datasets/annotations/nlp5/v1/{README.md,schema.json,qa_examples.json}`
- `tests/unit/test_nlp5_qa.py`
- `tests/integration/test_nlp5_real_qa.py`
- `scripts/evaluate_nlp5.py`
- `reports/nlp5_real_qa.json`
- this report

Modified:

- `services/nlp/evaluation/__init__.py`
- `docs/ARCHITECTURE.md`
- `docs/EVALUATION_PLAN.md`
- `docs/DECISIONS.md`
- `docs/MODEL_REGISTRY.md`
- `docs/NLP_MASTER_PLAN.md`

No file under `indicnotice/schemas/` changed.

## 6. Question routing

The deterministic router covers deadline, date, fee, documents, authority,
URL, eligibility, qualification, procedure, action, benefit, venue and other
notice questions. Script-based question-language detection supports English,
Hindi and Telugu. Venue routing is deliberately narrow so “Where can I apply?”
routes to URL while “Where is the exam?” routes to venue.

## 7. Structured-field answering

Canonical fields are consulted before retrieval or generation for application
deadlines, typed exam/interview dates, fees, required documents, issuing
authority, application links, qualifications and benefits. Fee answers use
`FeeItem` and cannot confuse an income threshold with an application fee.
Date answers select the requested `DateRole`, not the chronologically latest
date.

## 8. Eligibility QA

Eligibility questions always call the existing deterministic evaluator and
explanation layer. PASS, FAIL, UNKNOWN and NOT_APPLICABLE are preserved.
Condition explanations include requirement, candidate/computed value, status,
reason, evidence IDs and source pages. The natural-language wrapper never
changes the evaluator decision and does not claim an official decision.

## 9. Missing-information handling

UNKNOWN eligibility responses expose the exact missing candidate attributes.
Guarded conditions are respected, and missing data from an irrelevant OR branch
is not requested after another branch has passed. If the notice has no
eligibility AST, the service returns `NOT_STATED` rather than inventing rules.

## 10. Procedure/action QA

Procedure questions use `get_action_execution_order` over canonical
`ActionNode` dependencies. Optional and conditional nodes are labeled, parallel
nodes remain dependency-safe, cycles fail explicitly, and evidence from all
used action nodes is cited.

## 11. Retrieval baseline

`unicode-bm25-nlp5-v1` performs Unicode-aware tokenization, preserves Indic
combining marks, removes a small stopword set and applies bounded cross-lingual
concept expansion. It ranks complete `EvidenceSpan` units in memory using
actual BM25 scores. Each result preserves `document_id`, page, block, evidence
ID, text, score and method. No fabricated scores or arbitrary token chunks are
used.

## 12. Optional embedding retrieval

NOT SELECTED. No safe, already-usable local embedding backend was present.
BGE-M3 and multilingual E5 therefore remain unintegrated and are recorded as
`NOT_SELECTED` for NLP-5. The milestone does not require a vector database, and
the lexical baseline met the required real Hindi/Telugu retrieval smoke gate.

## 13. Grounded generation

An optional provider-neutral generator adapter is implemented. It receives
only the question and up to five retrieved evidence spans within an 8,000
character bound. Its strict Pydantic output contains answer text, citation IDs
and an abstention flag. Empty bounded context, malformed JSON, schema errors,
timeouts and provider failures fail closed.

The real NLP-5 run used structured/extractive answering and did **not** run
Qwen for QA. No QA generator backend was added to the model registry; Qwen's
separate NLP-3 extraction status remains `TESTED` and is not extrapolated.

## 14. Citation validation

Every generated citation must be in the retrieved subset, exist in the current
analysis and belong to the current document. Factual generated answers require
at least one citation. Numbers, monetary values, percentages, ages, date
components and URLs in generated answers must occur in cited evidence or the
answer is rejected. This automatic validation is not mislabeled as human
semantic support review.

## 15. Abstention / NOT_STATED

Missing canonical facts and retrieval misses return a localized
`NOT_STATED` response with `UNANSWERABLE` and `abstained=true`. The real Hindi
interview-venue and Telugu exam-venue questions both abstained without using
issuer addresses or outside knowledge.

## 16. Partial-answer handling

When a typed exam/interview date exists but its venue does not, the service
returns the cited date, explicitly states that the venue is absent and uses
`PARTIALLY_DETERMINABLE` / `PARTIAL`. Partial behavior is distinct from both
fully answerable and fully unanswerable states.

## 17. Multilingual query handling

English, Hindi and Telugu questions are routed by deterministic multilingual
rules. Cross-language structured questions work because routing resolves to
canonical fields. Lexical retrieval uses a bounded concept lexicon rather than
silently translating the notice. Answers follow the question language for the
localized structured and abstention templates; generic extractive answers
preserve source evidence wording. Romanized Indic remains optional and limited.

## 18. Real Hindi examples

- Structured: Hindi deadline question returned `2025-10-15` from
  `dates.application_deadline` with its page-1 evidence citation.
- Retrieval: annual-family-income question returned cited Hindi source text;
  the top BM25 result scored `2.8840451341943107`.
- Unanswerable: interview venue returned `NOT_STATED` with no fabricated
  citation.

## 19. Real Telugu examples

- Structured: Telugu deadline question returned `2025-03-21` with its page-1
  evidence citation.
- Retrieval: admission-preference question returned cited source evidence;
  the top BM25 result scored `6.535578828963006`.
- Unanswerable: Telugu exam-venue question returned localized `NOT_STATED`
  with no fabricated citation.

## 20. Eligibility example

For the real Hindi notice, profile `{marks_percentage: 60,
annual_family_income_inr: 300000}` produced deterministic PASS with two
eligibility evidence citations. Omitting income produced UNKNOWN/PARTIAL and
exactly `annual_family_income_inr` in `missing_information`.

## 21. QA annotation set

The review set has 30 items: 15 over the Hindi notice and 15 over the Telugu
notice. Question languages are 11 English, 10 Hindi and 9 Telugu. Candidate
answerability labels are 20 ANSWERABLE, 3 PARTIAL and 7 UNANSWERABLE; 10/30
(33.3%) are partial or unanswerable. All 30 are
`NEEDS_HUMAN_VERIFICATION`. Every referenced evidence ID exists, but no item is
claimed as human gold.

## 22. Evaluation tooling

The QA evaluator supports answerability accuracy, normalized exact match,
token F1, citation validity, human-verified citation support, unsupported-answer
rate, abstention accuracy, eligibility decision correctness and exact missing
field correctness. Date normalization equates alternate formats only when the
remaining semantic text also matches, so application deadline and exam date
are not collapsed. Retrieval evaluation implements Recall@k and MRR. All
quality metrics are gated to annotations whose state is exactly `VERIFIED`.

## 23. Retrieval results

There is no human-verified retrieval ground truth in the NLP-5 set, so real
Recall@k and MRR are **NOT SCORED**. Unit tests verify the calculations on
synthetic known relevance. The real smoke run records actual ranks and scores:
the Hindi income case top score was `2.8840451341943107`; the Telugu preference
case top score was `6.535578828963006`. These are execution evidence, not
quality claims.

## 24. QA results

QA quality metrics are **NOT SCORED** because `verified_items=0`. Descriptive
real-smoke results only: 8 cases, 8/8 with valid citations or valid abstention,
2 abstentions, and mode counts of 2 STRUCTURED_FACT, 2 EVIDENCE_RETRIEVAL,
2 NOT_STATED and 2 ELIGIBILITY_RESULT. No result is presented as held-out gold
accuracy.

## 25. Hallucination / abstention analysis

Runtime checks reject invented/non-retrieved evidence IDs and unsupported
critical numeric or URL claims. Prompt-injection-like notice text cannot become
a structured fee when the canonical fee field is absent. Invalid generator
output and provider failures convert to safe abstention. The two real
unanswerable smoke questions both abstained. Full semantic hallucination rate
remains unscored until human verification supplies answer and support truth.

## 26. Failure analysis

- `hi-q13` is candidate-labeled PARTIAL around an untyped `dates.other` value,
  while the service conservatively returns UNANSWERABLE because it cannot prove
  the requested exam role. This is a typed-date ambiguity for human review.
- `te-q14` is candidate-labeled PARTIAL, while current routing returns the
  canonical application deadline as ANSWERABLE. The question mixes “where” and
  submission timing and exposes a compound-intent limitation.
- The real Hindi income retrieval answer includes a noisy top span before the
  exact threshold span. Citation validity passes, but extractive concision and
  ranking quality need verified relevance judgments.
- Generic extractive answers preserve source wording rather than guaranteeing
  fluent output in the question language. Bounded lexical expansion cannot
  cover all cross-language paraphrases.

These are candidate-label comparisons only, not measured errors against gold.

## 27. Tests added

Thirty-seven NLP-5 unit cases and two real-fixture integration cases cover:
routing, structured facts, typed dates, fee disambiguation, mandatory/optional/
conditional/alternative documents, action order, PASS/FAIL/UNKNOWN eligibility,
missing attributes, OR behavior, lexical and cross-lingual ranking, extractive
answers, abstention, partial answers, answer language, injection-like evidence,
multiple citations, invalid citations, unsupported numbers, bounded generation,
invalid model output, timeouts/offline failure, QA metrics and verified-only
scoring.

## 28. Commands executed

Principal reproducible commands:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/unit/test_nlp5_qa.py tests/integration/test_nlp5_real_qa.py -q
.\.venv\Scripts\python.exe scripts/evaluate_nlp5.py
.\.venv\Scripts\python.exe -m compileall -q services/nlp/qa services/nlp/retrieval services/nlp/evaluation/qa_metrics.py scripts/evaluate_nlp5.py
```

JSON validation also confirmed 30 items, balanced notice coverage, explicit
verification states and zero missing evidence references.

## 29. Final test results

- Full suite: **302 passed, 2 skipped, 0 failed** in 64.39 seconds.
- Focused NLP-5 suite: **39 passed, 0 failed**.
- Skips are the opt-in real Qwen NLP-3 inference tests.
- One non-functional warning remains: Windows denied pytest cache writes under
  `.pytest_cache`. Test collection and execution completed successfully.

## 30. Known limitations

- No QA item is human verified, so no quality metric is available.
- Only two recorded real notices are used for smoke execution.
- Cross-lingual lexical retrieval depends on a small explicit concept lexicon.
- Generic extractive answers may be long/noisy and may retain the source
  language instead of fully matching the query language.
- The optional real generative QA path and multilingual embedding retrieval
  were not run.
- Single-turn QA only; no conversational memory or transliteration backend was
  added.
- Numeric/URL support checks are strong automatic guards but do not prove full
  semantic entailment or prompt-injection immunity.

## 31. Contract-change requests

NONE

QA and retrieval contracts remain in the service layer. Canonical
`NoticeAnalysis` schema version 1.0 remains frozen.

## 32. NLP-5 acceptance checklist

1. PASS — all pre-existing tests remain green.
2. PASS — all new NLP-5 tests pass.
3. PASS — canonical structured fields precede generation.
4. PASS — eligibility routes to the deterministic evaluator.
5. PASS — PASS/FAIL/UNKNOWN semantics are tested and preserved.
6. PASS — exact missing profile attributes are surfaced.
7. PASS — procedure QA uses the canonical action graph.
8. PASS — document mandatory/optional/conditional/alternative semantics persist.
9. PASS — interpretable lexical evidence retrieval exists.
10. PASS — real Hindi retrieval executed.
11. PASS — real Telugu retrieval executed.
12. PASS — optional generation receives only bounded retrieved evidence.
13. PASS — generated citations are validated against retrieval and document.
14. PASS — unsupported critical numeric claims are rejected.
15. PASS — `NOT_STATED` is implemented and tested.
16. PASS — partial answers are implemented and tested.
17. PASS — real Hindi unanswerable question abstained.
18. PASS — real Telugu unanswerable question abstained.
19. PASS — real candidate-specific eligibility ran end-to-end.
20. PASS — every QA annotation has a verification state.
21. PASS — generated candidates are not claimed as gold.
22. PASS — multi-metric QA evaluation tooling exists.
23. PASS — unsupported-answer/hallucination evaluation support exists.
24. PASS — citation-validity evaluation exists.
25. PASS — no frontend or product layer was built.
26. PASS — NLP-6 was not started.

## 33. Recommended NLP-6 next step

Have humans verify or correct the 30 NLP-5 QA items and the carried-over 20
NLP-4 semantic items, freezing explicit answerability, accepted answers and
supporting evidence before any final scoring. Then define the locked NLP-6
protocol and run comparative retrieval/QA evaluation. This recommendation does
not begin NLP-6.

# IndicNotice NLP-4 Milestone Report

## 1. Final status

PASSED.

NLP-4 is complete as `evidence-gated-semantic-nlp4-v1`. Canonical schema
version 1.0 remains frozen, the full suite is green, Hindi and Telugu real
fixtures execute, and NLP-2/NLP-3 remain independently runnable. No NLP-5 or
product functionality was started.

## 2. Executive summary

NLP-4 adds a conservative semantic layer for eligibility and procedural
actions. It combines the NLP-2 deterministic baseline, bounded semantic rules,
and optional NLP-3 outputs treated only as candidates. Claims pass
field-specific evidence, value, operator, concept and conflict checks before
promotion. The canonical output remains `NoticeAnalysis` 1.0; promotion,
conflict, rejection and explanation records are service-only sidecars.

Twenty-six substantive tests cover semantic boundaries and end-to-end
evaluation. The final full run produced 263 passed, 2 skipped and 0 failed.

## 3. Starting baseline

Pre-flight read all required architecture, contract, decision, model,
evaluation and milestone documents; inspected schemas, evaluators, extractors,
validators, annotations, tests and the NLP-3 output. The independent baseline
run was 237 passed, 2 opt-in integration tests skipped, 0 failed (60.80 s).
NLP-3 was checkpointed before substantial NLP-4 work as commit `a9bb18f`.

## 4. NLP-3 findings carried forward

The finding is preserved without reinterpretation: Qwen3-4B Q4_K_M was
structurally integrated but was not quality-superior or production-ready. All
11 real chunks needed the allowed repair. Diagnostics recorded 64 post-repair
claim rejections; two surviving automatic support failures bring the observed
unsupported total to 66. There were 22 exact-text evidence realignments.

On verified data, NLP-2 versus NLP-3 category F1 was 1.000 versus 0.500 and fee
F1 was 1.000 versus 0.000. Evidence-reference validity was 116/116, confirming
that valid citations alone do not establish semantic correctness.

## 5. NLP-4 architecture

The pipeline is:

```text
NLP-1 Document/Evidence
  -> NLP-2 exact deterministic facts
  -> bounded NLP-4 semantic rules
  -> optional NLP-3 candidates
  -> evidence + semantic + field gates
  -> deterministic normalization/conflict handling
  -> NoticeAnalysis 1.0 + SemanticDiagnostics
  -> evaluator + deterministic evidence-linked explanation
```

`EvidenceGatedSemanticExtractor.extract_ingestion` runs without a contextual
input or accepts a recorded/live NLP-3 `NoticeAnalysis` candidate.

## 6. Files created/modified

Created semantic candidate/diagnostic, canonicalization, relaxation, support,
rule and hybrid extraction modules under `services/nlp/semantic/`; deterministic
explanations under `services/nlp/eligibility/`; semantic metrics under
`services/nlp/evaluation/`; the NLP-4 runner; 20-example review data and schema;
synthetic candidate profiles; 26 tests; a real-run report; and this report.

Updated `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACTS.md`, `docs/DECISIONS.md`,
`docs/EVALUATION_PLAN.md`, `docs/NLP_MASTER_PLAN.md`, and the evaluation export.
`docs/MODEL_REGISTRY.md` was intentionally unchanged because no model status
changed. No file under `indicnotice/schemas/` changed.

## 7. Evidence-gating policy

Contextual claims are candidates regardless of JSON validity, cited ID or
model confidence. Eligibility groups, documents and actions pass exact source
reference and field-specific support gates. Rejections use
`INVALID_EVIDENCE`, `UNSUPPORTED_VALUE`, `UNSUPPORTED_OPERATOR`,
`UNSUPPORTED_ATTRIBUTE`, `SCHEMA_INVALID`, `DUPLICATE`, `CONFLICT`, or `OTHER`.
Rejected candidates stay out of canonical output and remain auditable.

## 8. Field-specific trust hierarchy

Explicit URLs, exact date values and exact money values use deterministic
parsing precedence. Contextual role or complex-logic candidates can add only
supported, non-conflicting semantics. Eligibility checks require concept,
threshold, inclusivity and reference-date evidence. Action optionality,
conditionality and dependency edges require explicit cues. There is no
universal confidence cutoff and no generated probability is trusted.

## 9. Eligibility semantic extraction

Bounded Hindi/Telugu/English rules handle age, income and marks comparators;
qualification alternatives; category/state/boolean requirements; cutoff dates;
birth windows; guards; and nested groups. Exact operator mapping preserves
`<`, `<=`, `>`, and `>=`. Preference/desirable wording is excluded from
mandatory eligibility and recorded as unresolved review material.

## 10. Relaxations and exemptions

`resolve_age_delta` combines a supported base maximum with a stated category
delta. It emits mutually exclusive guarded general and relaxed branches, never
`age <= base AND age <= relaxed`. Without a supported base it abstains and
records an unresolved item. `apply_age_exemption` uses a guard so exempt
profiles become `NOT_APPLICABLE`. Tests cover SC age 33 PASS, general age 33
FAIL, unknown category UNKNOWN, unresolved delta, and PwD exemption.

## 11. Cutoff-date handling

Age with `reference_date` continues through the frozen deterministic evaluator,
which derives completed calendar years from date of birth and ignores a
supplied current-age value. Boundary tests cover an exact 30th birthday,
30 years plus one day (still 30 completed years), and a completed age of 31.
Birth-date windows use `BETWEEN` with normalized ISO endpoints.

## 12. Logical AST handling

Canonicalization ignores unstable IDs and source metadata, normalizes values,
and sorts AND/OR siblings because those operators are commutative. It preserves
nesting, guards, negation and reference dates. Tests prove `A AND B` equals
`B AND A` while `A AND (B OR C)` differs from `(A AND B) OR C`. No general
theorem prover was introduced.

## 13. Candidate evaluator integration

The existing four-state evaluator remains the only candidate decision engine.
Missing attributes and unknown guards remain UNKNOWN; non-applicable guarded
branches remain neutral. End-to-end tests run extracted marks/income rules
against PASS, FAIL and UNKNOWN profiles. Non-sensitive profile fixtures cover
relaxation, exemption, multiple degrees and exact thresholds.

## 14. Deterministic explanation layer

`explain_eligibility` wraps evaluator results without generative text. Each
condition explanation contains the normalized requirement, supplied value,
computed cutoff age where applicable, PASS/FAIL/UNKNOWN/NOT_APPLICABLE result,
deterministic reason, evidence IDs and source pages. User-facing summaries say
“Appears eligible…”, “Does not meet…”, or “Cannot determine…”, never a
government eligibility guarantee.

## 15. Action extraction

NLP-4 recognizes existing canonical action types for registration, obtaining
documents, uploading, fee payment, submission, downloads, exams, interviews
and verification. Unsupported product actions are not added to the frozen enum;
representable existing types are used. Conditional actions carry
`applies_when`, optional wording sets `is_optional`, and links/deadlines remain
canonical references only when supplied by supported extraction.

## 16. Action dependencies

Edges require explicit ordering terms such as before, after or then. Register →
upload → submit and pay → submit are representable. Multiple separately parsed
document-acquisition actions can remain parallel predecessors of upload; no edge
is inferred merely from sentence order. Existing cycle/dangling validation and
topological ordering remain active and tested.

## 17. Hybrid conflict handling

Canonical duplicates are rejected as duplicates. A supported contextual
eligibility group that overlaps deterministic attributes but differs is
recorded as a `SemanticConflict` and rejected pending review. Category, dates,
fees and links similarly retain deterministic values and surface conflicts.
Warnings summarize conflicts; nothing is silently overwritten by the model.

## 18. Contextual-claim rejection analysis

In the two-document NLP-4 run, 26 contextual candidates reached the NLP-4
merge gate: 9 were promoted and 17 rejected. Rejections were 11
`UNSUPPORTED_ATTRIBUTE` and 6 `CONFLICT`; other taxonomy counts were zero. This
is a candidate-flow diagnostic, not an accuracy metric and not directly
comparable in denominator to NLP-3's 66 observed unsupported claims.

The dominant NLP-3 error pattern was semantic mis-typing despite valid evidence:
admission versus scholarship, spurious fees, and procedural sentences mapped
to unsupported actions. That finding motivated concept-specific gates.

## 19. Real Hindi execution

The SCERT Haryana NMMSS 2025 Hindi PDF passed canonical NLP-1 ingestion and
NLP-4 extraction. NLP-4 produced two eligibility conditions and four actions,
surfaced four conflicts, and emitted no unresolved semantic item. Verified
category/fee evaluation remained correct. This is a real-document execution,
not proof that its unverified semantic candidates are gold.

## 20. Real Telugu execution

The KVS Kadapa 2025 Telugu/English admission PDF passed canonical NLP-1
ingestion and NLP-4 extraction. It produced four actions and no promoted
eligibility condition; one preference/desirable span was conservatively left
unresolved. Six promoted and seven rejected decisions (including deterministic
decisions in the per-document total) were recorded, with two conflicts. The
absence of eligibility output is an abstention, not an invented rule.

## 21. Gold/verification status

`datasets/annotations/nlp4/v1/semantic_examples.json` contains 20 reviewable
examples: 10 Hindi and 10 Telugu. The format includes document/language,
verbatim evidence, atomic conditions, groups, guards, actions and edges. Every
example is `NEEDS_HUMAN_VERIFICATION`; none is described or scored as gold.
Only pre-existing `verified_complete` category/fee fields enter real metrics.

## 22. Eligibility evaluation

Implemented separate condition precision/recall/F1, attribute accuracy,
operator accuracy, value accuracy, reference-date accuracy, logical-structure
correctness and guard correctness. Metric behavior is unit-tested. Research
scores are intentionally `NOT_SCORED` until the dedicated semantic candidates
are human-verified.

## 23. Action evaluation

Implemented action identification precision/recall/F1, dependency-edge
precision/recall/F1, optional-action accuracy, conditional-action accuracy and
deadline-association accuracy. Metric behavior is unit-tested separately from
eligibility metrics. No score is claimed on unverified action annotations.

## 24. End-to-end candidate decision evaluation

Tests cover notice text → semantic extraction → canonical AST → deterministic
PASS/FAIL/UNKNOWN decisions, plus direct verified mechanics for cutoff age,
delta relaxation, exemptions, alternatives and boundaries. These are synthetic
regression/evaluation fixtures, not a reported real-corpus accuracy result.

## 25. NLP-2 vs NLP-3 vs NLP-4 comparison

Only verified fields are shown:

| Field | NLP-2 F1 / EM | NLP-3 F1 / EM | NLP-4 F1 / EM |
|---|---:|---:|---:|
| Category (2 documents) | 1.000 / 1.000 | 0.500 / 0.500 | 1.000 / 1.000 |
| Fees (1 verified item) | 1.000 / 1.000 | 0.000 / 0.000 | 1.000 / 1.000 |
| Eligibility/actions | N/A | N/A | N/A — awaiting human verification |

NLP-4's verified result follows its deterministic precedence policy; it is not
presented as proof of general semantic superiority.

## 26. Tests added

Twenty-six NLP-4 tests cover operator boundaries; calendar age; category and
delta relaxation; missing base; exemption; unknown guard behavior; nested AST
canonicalization; qualification OR; preference/desirable exclusion; evidence
value/operator checks; birth windows; parallel/optional/ordered actions; action
cycles; optional/conditional documents; contextual rejection, conflict and
promotion; evidence-linked explanations; separate metrics; and end-to-end
candidate decisions.

## 27. Commands executed

Key reproducible commands:

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m pytest tests/unit/test_nlp4_semantics.py -q
.venv\Scripts\python scripts/evaluate_nlp4.py
.venv\Scripts\python -m compileall -q services/nlp/semantic services/nlp/eligibility
```

Pre-flight also inspected Git status and the recorded NLP-3 JSON, then created
the required clean NLP-3 checkpoint commit.

## 28. Final test results

Final result: **263 passed, 2 skipped, 0 failed in 58.42 seconds**. The two
skips are the existing opt-in real-model NLP-3 integration tests. Pytest emitted
one non-test failure warning because Windows denied cache writes under
`.pytest_cache`; it did not affect collection or execution. JSON and diagnostic
invariants passed, and both real languages were present in the report.

## 29. Known limitations

- The 20 semantic annotations still require independent human verification.
- Support heuristics improve precision but do not prove full natural-language
  entailment.
- The real smoke set contains only two documents and has verified gold only for
  category/fees; semantic quality cannot yet be quantified.
- Integer completed-year age follows the frozen evaluator and public-notice
  convention; sub-year duration comparisons are not a separate schema feature.
- Action vocabulary remains the frozen enum, so finer labels such as
  `send_by_post` or `attend_counseling` map to existing representable types or
  abstain rather than triggering a contract change.

## 30. Contract-change requests

NONE. Schema version 1.0 and all frozen Pydantic contracts remain unchanged.

## 31. NLP-4 acceptance checklist

1. PASS — all pre-existing tests remain green.
2. PASS — all new NLP-4 tests pass.
3. PASS — schema 1.0 remains frozen.
4. PASS — NLP-2 remains independently runnable.
5. PASS — NLP-3 remains independently runnable.
6. PASS — NLP-4 is separately runnable.
7. PASS — exact numeric inclusivity is preserved.
8. PASS — category relaxation works.
9. PASS — known-base delta relaxation works.
10. PASS — missing candidate information stays UNKNOWN.
11. PASS — cutoff-date age works end to end.
12. PASS — qualification alternatives use OR.
13. PASS — preference/desirable text is not made mandatory.
14. PASS — exemptions have tested guarded handling.
15. PASS — nested AND/OR is represented and evaluated.
16. PASS — explanations are deterministic and evidence-linked.
17. PASS — supported action dependencies are represented.
18. PASS — parallel actions are supported.
19. PASS — optional actions are supported.
20. PASS — unsupported contextual claims are rejected.
21. PASS — deterministic/contextual conflicts are surfaced.
22. PASS — real Hindi execution succeeds.
23. PASS — real Telugu execution succeeds.
24. PASS — eligibility semantic evaluation exists.
25. PASS — action/dependency evaluation exists.
26. PASS — extracted-rule → candidate-decision tests exist.
27. PASS — human verification state is explicit.
28. PASS — unverified annotations are not claimed as gold.
29. PASS — no NLP-5 or product functionality was started.

## 32. Recommended NLP-5 next step

Do not start NLP-5 until a human reviewer adjudicates the 20-example semantic
set and the results are versioned. The next milestone should then use the
verified canonical fields and evidence for schema-first grounded QA with an
explicit NOT_STATED outcome, without reopening NLP-4 or trusting raw model
claims.

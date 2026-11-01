# IndicNotice NLP-3 Milestone Report

## 1. Final status

PASSED

The engineering acceptance gate is satisfied: a real pretrained multilingual
model executed successfully on real Hindi and Telugu public-notice content,
returned canonical `NoticeAnalysis` 1.0 results, and was compared independently
with NLP-2. This is not a quality-superiority verdict. On the small scoreable
slice, NLP-3 underperformed NLP-2.

## 2. Executive summary

NLP-3 adds a provider-neutral, evidence-grounded contextual extractor behind
the frozen `StructuredExtractor` interface. It consumes canonical NLP-1
documents and evidence, uses versioned prompts and constrained JSON generation,
validates structure and provenance, allows one repair per chunk, rejects
unsupported claims, and deterministically converts and merges results into the
unchanged schema 1.0.

The primary backend is Qwen3-4B Q4_K_M through a pinned local llama.cpp Vulkan
runtime. Genuine inference completed on one Hindi and one Telugu/English public
notice. The final two-document verified-only smoke comparison favored NLP-2:
category F1 was 1.000 vs 0.500 and fee F1 was 1.000 vs 0.000. NLP-3 achieved
116/116 valid canonical evidence references, but automatic support is not a
substitute for manual semantic citation review.

## 3. Starting repository baseline

- Repository root: `<repository-root>`.
- Starting commit: `4596ea5 Complete NLP-2 interpretable extraction baseline`.
- Starting Git worktree: clean.
- Independent pre-change test run: 226 passed, 0 failed in 49.31 seconds.
- NLP-0 remained frozen; NLP-1 and NLP-2 implementations were inspected and
  retained.
- The NLP-2 checkpoint was already committed, so no additional checkpoint was
  required.

## 4. Model selection

- Model repository: `Qwen/Qwen3-4B-GGUF`.
- Revision: `bc640142c66e1fdd12af0bd68f40445458f3869b`.
- File: `Qwen3-4B-Q4_K_M.gguf`.
- Model SHA-256:
  `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.
- Provider: local llama.cpp OpenAI-compatible HTTP endpoint.
- Runtime: llama.cpp release `b11429`, commit
  `d81235049384534c167caea52b85a694f6103d14`.
- Runtime archive SHA-256:
  `1bfe78ad9168b79fa02bf67f6af9f5e17a966d824d77238517f7bef12ac73b36`.
- License/access: Apache-2.0; public local checkpoint, no API credential.
- Runtime hardware: NVIDIA GeForce RTX 4050 Laptop GPU, 6,141 MiB, driver
  581.86; Windows 11; Python 3.12.10.
- Languages actually tested: Hindi and Telugu/English mixed notice content.

The model was chosen because its official card lists Hindi and Telugu support,
the 4B quantization fits the available laptop GPU, local execution avoids
credential/data-transfer concerns, and llama.cpp supports JSON-schema
constrained generation. TESTED denotes successful real execution, not adequate
task accuracy.

## 5. Architecture implemented

```text
NLP-1 Document + EvidenceSpan[]
  -> deterministic complete-unit chunks
  -> versioned prompts
  -> StructuredModelProvider
  -> constrained JSON response
  -> Pydantic transport validation
  -> evidence/value validation
  -> one bounded repair
  -> unsupported-claim rejection
  -> deterministic normalization and merge
  -> NoticeAnalysis 1.0 + diagnostics
```

The contextual package does not import the NLP-2 baseline. Both systems receive
the same `IngestionResult` in the comparison runner.

## 6. Files created/modified

Created:

- `services/nlp/extraction/contextual/__init__.py`
- `services/nlp/extraction/contextual/context.py`
- `services/nlp/extraction/contextual/errors.py`
- `services/nlp/extraction/contextual/extractor.py`
- `services/nlp/extraction/contextual/provider.py`
- `services/nlp/extraction/contextual/schema.py`
- `services/nlp/extraction/contextual/types.py`
- `services/nlp/extraction/contextual/prompts/system_v1.txt`
- `services/nlp/extraction/contextual/prompts/extraction_v1.txt`
- `services/nlp/extraction/contextual/prompts/repair_v1.txt`
- `services/nlp/evaluation/contextual_metrics.py`
- `scripts/evaluate_nlp3.py`
- `tests/unit/test_nlp3_contextual.py`
- `tests/integration/test_nlp3_real_model.py`
- `reports/nlp3_real_evaluation.json`
- `NLP3_MILESTONE_REPORT.md`

Modified:

- `services/nlp/evaluation/__init__.py`
- `services/nlp/evaluation/extraction_metrics.py`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/EVALUATION_PLAN.md`
- `docs/MODEL_REGISTRY.md`

No frozen canonical schema file was changed.

## 7. Prompt design

Prompt version `indicnotice-contextual-v1` is stored in three files: system,
initial extraction, and repair. The system prompt treats document text as
untrusted data, forbids following embedded instructions, forbids world-knowledge
completion, requires null/empty abstention, preserves inequalities and critical
values, and permits only supplied evidence aliases. A prompt-injection-like
document block is covered by unit tests. One test does not establish perfect
prompt-injection security.

## 8. Context/chunking strategy

Evidence spans are sorted by page, character offset, block, and evidence ID.
Complete evidence units are packed without truncation. The default maximum is
3,000 rendered characters; a single unit beyond the hard limit raises
`ContextTooLarge`. Each chunk retains document/page/block provenance through its
canonical evidence mapping. Compact aliases (`E000001`, etc.) reduce prompt
cost and map deterministically back to full IDs.

The real Hindi document used 7 chunks and Telugu used 4. An earlier
6,000-character setting exhausted the 4,096-token generation ceiling on a Hindi
chunk, so the empirically safer value became the default.

## 9. Structured-output strategy

llama.cpp receives an explicit JSON schema. Top-level objects and field items
are strict; eligibility uses a bounded-depth generation grammar, followed by
the full recursive Pydantic transport contract. Extra fields and invalid enum or
scalar types fail validation. JSON is parsed normally; there is no permissive
substring extraction or guessed JSON repair.

Each chunk gets an initial request and at most one repair. If structural output
is still invalid, `SchemaValidationFailure` is raised. Typed provider timeout,
unavailability, evidence, and context-size failures are also exposed.

## 10. Evidence grounding

Only aliases supplied with a chunk can resolve to canonical evidence IDs.
Validators check document membership, exact source strings, normalized dates
and times, monetary values, URLs, document-alternative cues, and explicit
dependency cues. Exact-text evidence realignment may correct a citation but
never changes a generated semantic value.

After the sole repair, unsupported individual claims are removed and counted;
the canonical output carries an `unsupported_model_claims_rejected` warning.
Malformed structure still fails. Raw responses and per-attempt diagnostics are
retained in the public-fixture evaluation artifact.

## 11. Eligibility extraction

The transport model supports recursive AND/OR groups, atomic conditions,
comparators including `<`, `<=`, `>`, `>=`, `IN`, and `BETWEEN`, reference
dates, exception links, and guarded applicability groups. Conversion produces
the frozen `Condition`/`ConditionGroup` AST. Candidate eligibility is never
decided by the generative extractor and remains deterministic downstream.

The generation grammar is intentionally bounded for runtime reliability; full
recursive validity is enforced afterward. Cross-chunk groups are joined with
AND and an explicit review warning because global logic may be ambiguous.

## 12. Action/procedure extraction

The model may extract canonical action types, descriptions, document/fee/date
references, channels, URLs, optionality, and explicit dependencies. Dependency
edges survive only when cited text contains an ordering cue and the referenced
action exists in the same chunk. Dangling dependencies are removed with a
warning. Arbitrary text order is not treated as a dependency.

## 13. Validation and normalization

Structural validation, evidence validation, and canonical validation are
separate stages. Date and money values must be deterministically supported.
Source-form `www.` URLs are converted to `https://www.` only after the exact
source form passes evidence validation, matching NLP-2's conservative policy.
Unknown information remains null/empty. No OCR text is corrected by NLP-3.

## 14. Merge/conflict handling

Source/chunk order determines merge order. Exact duplicates merge evidence IDs
and produce informational diagnostics. Scalar disagreements retain the earliest
candidate and emit `contextual_conflict` with all evidence; later chunks never
silently overwrite earlier values. Duplicate action identifiers after repair
are rejected. Canonical validation remains the final gate.

## 15. Real model inference

### Hindi

- Fixture: `scert_haryana_nmmss_2025_hindi.pdf`.
- Result: successful canonical schema 1.0 output.
- Chunks/attempts: 7/14; each chunk used its one repair.
- Model latency: 704.57 seconds.
- Tokens across attempts: 55,025 prompt; 29,617 completion.
- Evidence: 72/72 valid references; 51/53 automatically supported claims.
- Evidence realignments: 14.
- Unsupported/hallucination count: 52, including 50 claims rejected after
  repair and two surviving automatically unsupported claims.

### Telugu

- Fixture: `kv_kadapa_admission_2025_telugu.pdf`.
- Result: successful canonical schema 1.0 output.
- Chunks/attempts: 4/8; each chunk used its one repair.
- Model latency: 257.43 seconds.
- Tokens across attempts: 27,390 prompt; 11,283 completion.
- Evidence: 44/44 valid references; 18/18 automatically supported claims.
- Evidence realignments: 8.
- Unsupported/hallucination count: 14 rejected claims.

The combined report was regenerated from exact request/settings-hashed genuine
response checkpoints (22 cache hits, zero new inference calls). The original
Hindi and Telugu runs had cache misses and performed the measured GPU inference.

## 16. Fixture/gold annotation status

The registry contains 10 official fixtures: 5 Hindi and 5 Telugu. Across their
field annotations there are 13 `verified_complete`, 18 `verified_partial`, 3
`template_only`, and 2 `unverified` labels. The 13 complete labels are 10
categories, 2 notice numbers, and 1 fee field.

For the two real-model fixtures, only two category labels and the Hindi fee
label are scoreable. Partial date, eligibility, document, and action labels are
not treated as complete gold. No annotation was relabeled as human-verified.
Manual semantic evidence support remains NEEDS_HUMAN_VERIFICATION.

## 17. Evaluation protocol

NLP-2 and NLP-3 consume the identical canonical NLP-1 ingestion result for each
fixture. NLP-3 receives no baseline values or rules. `evaluate_extraction`
scores only fields marked `verified_complete`; `aggregate_reports` combines the
same document subset. Metrics are precision, recall, F1, and exact match per
field, plus evidence validity/support, unsupported-output count, schema status,
repairs, failures, latency, tokens, and evidence realignments.

## 18. NLP-2 baseline results

| Field | TP | FP | FN | Precision | Recall | F1 | Exact match |
|---|---:|---:|---:|---:|---:|---:|---:|
| category | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| fees | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 |

## 19. NLP-3 contextual results

| Field | TP | FP | FN | Precision | Recall | F1 | Exact match |
|---|---:|---:|---:|---:|---:|---:|---:|
| category | 1 | 1 | 1 | 0.500 | 0.500 | 0.500 | 0.500 |
| fees | 0 | 4 | 1 | 0.000 | 0.000 | 0.000 | 0.000 |

## 20. NLP-2 vs NLP-3 comparison

| Field | NLP-2 F1 | NLP-3 F1 | Interpretation |
|---|---:|---:|---|
| category | 1.000 | 0.500 | NLP-2 better on two verified documents |
| fees | 1.000 | 0.000 | NLP-2 better on one verified fee label |
| typed dates | N/A | N/A | insufficient verified-complete gold |
| documents | N/A | N/A | insufficient verified-complete gold |
| authority | N/A | N/A | insufficient verified-complete gold |
| URLs | N/A | N/A | insufficient verified-complete gold |
| eligibility | N/A | N/A | insufficient verified-complete gold |
| actions | N/A | N/A | insufficient verified-complete gold |

These are smoke results, not a statistically meaningful model ranking.

## 21. Evidence-grounding results

Canonical Evidence Reference Validity was 116/116 = 1.000. Automatic Evidence
Support was 69/71 = 0.972 overall (Hindi 0.962, Telugu 1.000). The automatic
metric checks exact strings and protected values. It does not prove semantic
entailment: the Hindi model cited real text for several wrongly typed fee items.
Manual Evidence Support Accuracy is therefore N/A pending human verification.

## 22. Hallucination analysis

Hindi produced 52 unsupported outputs by the implemented audit definition;
Telugu produced 14. Most were removed after the one repair, demonstrating that
ID-valid evidence alone is insufficient. Surviving false-positive fees included
real sentences about online application, category handling, and scholarship
application that did not semantically express the assigned fee facts. The model
also classified the Hindi scholarship notice as admission. These failures are
retained in the report rather than prompt-tuned away on the two fixtures.

## 23. Schema-validity / retry statistics

- Raw JSON/transport schema: 22/22 attempts structurally valid in the final
  recorded run.
- First-attempt evidence validity: 0/11 chunks.
- Repair rate: 11/11 chunks = 1.000.
- Final chunk evidence validity after repair/rejection: 11/11.
- Final canonical document schema validity: 2/2.
- Unrecoverable final-run document failures: 0/2.
- Retry bound: exactly one repair maximum per chunk.

Development failures included an unterminated response at the former larger
chunk size, an invalid recursive condition field before bounded grammar, and a
source-form URL rejected by canonical conversion before conservative URL
normalization. None was silently accepted.

## 24. Error analysis

The evaluation taxonomy now includes false positive, false negative, wrong
role, wrong operator, wrong value, wrong attribute, wrong logic, unsupported
hallucination, invalid/missing evidence, schema failure, duplicate, and conflict.
Observed scoreable errors were one category FP/FN pair and four fee FPs plus one
fee FN. Non-scoreable outputs still generated conflict, duplicate, chunk-merge,
evidence-realignment, and unsupported-claim warnings.

The dominant issue is semantic over-extraction rather than dangling citations.
Improving it requires broader verified data and stronger task adaptation, not
weaker validators.

## 25. Latency/resource observations

- Hindi: 704.57 model-seconds, 7 chunks, 84,642 total attempt tokens.
- Telugu: 257.43 model-seconds, 4 chunks, 38,673 total attempt tokens.
- Combined: 962.0 model-seconds and 123,315 attempt tokens.
- GPU after combined validation: 4,802 MiB of 6,141 MiB used.
- Local generation logs observed roughly 34-50 tokens/second depending on
  request; prompt-cache eviction occurred under memory pressure.

These values include repaired attempts and are hardware-specific observations,
not optimized benchmarks. NLP-2 remains dramatically cheaper.

## 26. Tests added

Unit tests cover canonical conversion/interface compatibility, complete-unit
chunking, hard context overflow, one bounded repair, unsupported-claim
rejection, hard schema failure, prompt-injection delimiting, `www.` URL
normalization after evidence validation, deterministic conflict handling,
provider timeout mapping, and baseline-import independence.

The gated real integration test covers actual Hindi and Telugu endpoint
inference. It is excluded from ordinary test runs unless
`INDICNOTICE_RUN_NLP3_REAL=1` is set; ordinary tests never call a remote or paid
model.

## 27. Commands actually executed

Key executed commands included:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\unit\test_nlp3_contextual.py
.\.venv\Scripts\python.exe -m compileall -q services\nlp\extraction\contextual services\nlp\evaluation
Invoke-RestMethod -Uri http://127.0.0.1:18089/health
.\.venv\Scripts\python.exe scripts\evaluate_nlp3.py --fixture datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf --output .tmp/nlp3_hindi_debug.json
.\.venv\Scripts\python.exe scripts\evaluate_nlp3.py --fixture datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf --output .tmp/nlp3_telugu_debug.json
.\.venv\Scripts\python.exe scripts\evaluate_nlp3.py --output reports/nlp3_real_evaluation.json
```

The initial 6,000-character Hindi development run and subsequent corrected
runs were also executed; failures and corrections are described above.

## 28. Final test results

- Unit/focused NLP-3 tests before final suite: 11 passed.
- Integration tests: the real endpoint test exists and is environment-gated in
  ordinary pytest; genuine inference was executed through the reproducible
  evaluation script instead of disguising mocks as integration.
- Real model smoke tests: Hindi passed; Telugu passed; combined artifact passed
  canonical validation.
- Full regression suite: 237 passed, 2 environment-gated real-model tests
  skipped, 0 failed in 62.99 seconds. This comprises all 226 pre-existing tests
  plus 11 new NLP-3 unit tests.

## 29. Known limitations

- The quantitative subset is only two documents and three verified field
  observations.
- Automatic exact evidence support is not semantic entailment.
- The tested 4-bit 4B model substantially over-extracted and underperformed the
  baseline on verified fields.
- Every chunk needed repair, creating high latency and token cost.
- Cross-chunk eligibility is conservatively AND-merged with a review warning;
  global discourse logic may require a stronger document-level strategy.
- The generation grammar bounds nesting depth for practical constrained
  decoding, although the frozen canonical AST remains recursive.
- No human gold expansion was fabricated; partial fields still need review.
- Table structure is limited by available NLP-1 evidence metadata.

## 30. Contract-change requests

NONE.

Schema 1.0 represented the validated outputs. All adaptations occurred in the
service-layer transport, validation, and normalization stages.

## 31. NLP-3 acceptance-gate checklist

1. Pre-existing tests remain green: yes; full suite 237 passed, 2 skipped,
   0 failed.
2. New NLP-3 tests pass: yes.
3. Real contextual pretrained model integrated: yes.
4. Real Hindi inference succeeds: yes.
5. Real Telugu inference succeeds: yes.
6. Canonical schema 1.0 validates: yes.
7. Critical fields retain valid evidence: yes, 116/116 references valid.
8. Prompt forbids world-knowledge filling and validators reject unsupported
   values: yes; remaining semantic errors are explicitly reported.
9. Structured-output failures are explicit: yes.
10. Retry behavior is bounded: yes, one repair per chunk.
11. Prompt files are versioned: yes.
12. Model/provider/settings documented: yes.
13. Long-document strategy implemented/tested: yes.
14. Chunk outputs merge deterministically: yes.
15. Conflicts are not silently overwritten: yes.
16. Eligibility uses the frozen AST: yes.
17. Operator distinctions are preserved by typed comparators/tests: yes.
18. Generative candidate eligibility decisions are absent: yes.
19. NLP-2 remains independently executable: yes.
20. Both methods use the same verified subset: yes.
21. Per-field evaluation exists: yes.
22. Hallucination/unsupported analysis exists: yes.
23. Evidence validity is measured: yes.
24. Schema/retry metrics exist: yes.
25. Unverified gold is not represented as verified: yes.
26. No product-layer or NLP-4 functionality started: yes.

## 32. Recommended NLP-4 next step

Do not start NLP-4 until this checkpoint is reviewed. When authorized, preserve
NLP-2 and NLP-3 as separate baselines and use the broader manually verified set
to decide whether a stronger model, task-specific fine-tuning, or a separately
labeled hybrid method is justified. Do not infer quality gains from this smoke
run.

# Controlled Pre-NLP-6 Corrective Audit Plan

## Scope and baseline

This plan was written before implementation changes. The repository and the two checked-in source PDFs are authoritative. The pre-change worktree was clean at `82ff9f4`; the repository interpreter was `<repository-root>\.venv\Scripts\python.exe` (Python 3.12.10), and the baseline was 302 passed, 2 expected opt-in Qwen skips, 0 failed. Canonical `NoticeAnalysis` schema 1.0 remains frozen, NLP-2/NLP-3/NLP-4/NLP-5 remain independent, evaluation annotations remain outside production inference, and NLP-6 is out of scope.

Source references below use PDF page numbers and canonical evidence block suffixes from fresh NLP-1 native extraction. “Code change” means a general rule with synthetic regression coverage, never fixture/document/QA/evidence-ID branching.

## Issue 8 — Mandatory-document semantic support

- **Observed symptom:** Ordinary mentions such as a prospectus or “visit the website for required-document details” can become mandatory `DocumentRequirement` objects.
- **Authoritative source evidence:** KVS p.1/b7 refers readers elsewhere for document details but enumerates none. SCERT p.2/b10-b12 and p.3/b20-b22 contain actual upload/submission relations for caste, disability, and post-selection income certificates.
- **Current code path:** `RegexBaselineExtractor._documents`, contextual `_validate_evidence`/`_sanitize_unsupported`, and `semantic.support.document_support`.
- **Current behavior:** `_DOCUMENT_CONTEXT` treats document nouns themselves as context; contextual validation checks source-name occurrence; NLP-4 mandatory support has no obligation/submission requirement.
- **Reproduction status:** Confirmed in the checked-in NLP-3/NLP-4 KVS and SCERT artifacts and by code inspection.
- **Root cause / layer:** Lexical occurrence is used as relation support; `NLP2_BASELINE`, `NLP3_CONTEXTUAL_VALIDATION`, `NLP4_SEMANTIC_SUPPORT`.
- **General fix proposal:** Require a recognized document entity plus clause-local obligation, attach, upload, submit, bring, or possession relation; reject referral/availability/issued-to-applicant contexts. Validate conditional guards.
- **Potential files affected:** baseline extractor, contextual extractor, semantic support, NLP-4 tests.
- **Regression risk:** Medium; terse list headings must still be supported when a nearby heading explicitly establishes requirements.
- **Code / annotation / schema:** Code must change; affected QA candidates must change; canonical schema must not change.
- **Tests required:** Referral-only, available prospectus, explicit upload, conditional caste upload, and document-list heading cases.
- **Status:** CONFIRMED — PLANNED.

## Issue 9 — Zero-fee negation validation

- **Observed symptom:** Arbitrary Hindi/Telugu/English negation supports contextual fee amount zero.
- **Authoritative source evidence:** SCERT p.2/b25 explicitly says no fee is charged; p.2/b12 is unrelated caste-certificate negation. KVS states no fee fact.
- **Current code path:** `ContextualStructuredExtractor._validate_amount` and `_sanitize_unsupported`.
- **Current behavior:** `value == 0` passes on any `no`, `nil`, `zero`, `नहीं`, `లేదు`, or `ఉచిత` cue without fee context.
- **Reproduction status:** Confirmed by code and NLP-3 `fee_002`/`fee_004` false claims.
- **Root cause / layer:** Negation and semantic target are not coupled; `NLP3_CONTEXTUAL_VALIDATION`.
- **General fix proposal:** Require a fee/charge/application-fee cue in the same bounded clause as the zero/negation cue.
- **Potential files affected:** contextual extractor and tests.
- **Regression risk:** Low to medium for unusual no-fee wording.
- **Code / annotation / schema:** Code must change; no annotation change solely for this bug; no schema change.
- **Tests required:** English/Hindi/Telugu explicit no-fee positives and unrelated-negation negatives.
- **Status:** CONFIRMED — PLANNED.

## Issue 10 — Null pseudo-dates

- **Observed symptom:** Generic headings yield many date-role objects with no value.
- **Authoritative source evidence:** SCERT p.1/b24 “exam details” supports no date; actual exam dates occur p.1/b7-b9 and p.3/b8-b10.
- **Current code path:** contextual date `_validate_evidence`, `_sanitize_unsupported`, `_convert_dates`.
- **Current behavior:** A null value bypasses normalized-date checks and is converted into canonical `TypedDate`.
- **Reproduction status:** Confirmed; the stored NLP-3 Hindi output contains numerous null date roles from one heading.
- **Root cause / layer:** Schema-nullability is mistaken for semantic support; `NLP3_CONTEXTUAL_VALIDATION`.
- **General fix proposal:** Reject date candidates without a supported normalized date/time. Preserve “announced later” only as warning/review information, not a fabricated typed date under current schema policy.
- **Potential files affected:** contextual extractor and tests.
- **Regression risk:** Low; deliberately unresolved dates will no longer be facts.
- **Code / annotation / schema:** Code must change; no candidate annotation change required; no schema change.
- **Tests required:** Generic heading, announced-later, and explicit dated exam.
- **Status:** CONFIRMED — PLANNED.

## Issue 11 — Category semantic support

- **Observed symptom:** Contextual category can survive on evidence-ID existence alone; generic application language can misclassify a scholarship/exam notice.
- **Authoritative source evidence:** SCERT p.1/b2-b4 is explicitly NMMSS scholarship examination/prospectus; KVS p.1/b1-b3 is admission schedule.
- **Current code path:** contextual evidence validation/sanitization and NLP-4 strong-field conflict recording.
- **Current behavior:** Category content is never checked against a category cue; NLP-3 labels SCERT admission.
- **Reproduction status:** Confirmed.
- **Root cause / layer:** Missing document-level category support policy; `NLP3_CONTEXTUAL_VALIDATION`, `NLP4_SEMANTIC_SUPPORT`.
- **General fix proposal:** Validate category against top/heading evidence and bounded category-specific cues; retain deterministic source-supported category and flag ambiguous evidence.
- **Potential files affected:** contextual extractor, semantic support/extractor, tests.
- **Regression risk:** Medium for multi-purpose notices.
- **Code / annotation / schema:** Code must change; no current annotation answer needs forced alignment; no schema change.
- **Tests required:** Scholarship/exam title versus generic application text, admission heading, ambiguous other.
- **Status:** CONFIRMED — PLANNED.

## Issue 12 — Contextual comparator contract

- **Observed symptom:** The structured grammar accepts `CONTAINS`, which canonical `Comparator` rejects, and omits canonical `NOT_EXISTS`.
- **Authoritative source evidence:** Executable enum in `indicnotice/schemas/eligibility.py` is authoritative.
- **Current code path:** `response_schema()` and `_convert_group`.
- **Current behavior:** Grammar/model validation may accept an operator without a deterministic conversion path.
- **Reproduction status:** Confirmed by direct contract comparison.
- **Root cause / layer:** Duplicated comparator vocabulary drift; `NLP3_CONTEXTUAL_CONTRACT`.
- **General fix proposal:** Generate the grammar enum from the canonical enum and add an exact synchronization test.
- **Potential files affected:** contextual schema and tests.
- **Regression risk:** Low; grammar changes require a real NLP-3 rerun only if new model output is requested. Cached candidates remain usable for downstream fixes.
- **Code / annotation / schema:** Code must change; annotations do not; canonical schema does not.
- **Tests required:** Exact enum equality and deterministic conversion for every accepted value.
- **Status:** CONFIRMED — PLANNED.

## Issue 13 — URL tokenization/canonicalization

- **Observed symptom:** Adjacent Indic text is swallowed by ASCII URLs.
- **Authoritative source evidence:** SCERT p.3/b2 contains `www.scertharyana.gov.in` immediately followed by corrupted/adjacent Hindi text; the host ends at `.in`.
- **Current code path:** baseline `_URL`/`_links`, contextual `_canonical_url` and link conversion.
- **Current behavior:** `[^^\s...]` accepts arbitrary Unicode suffixes and punctuation trimming is incomplete.
- **Reproduction status:** Confirmed in the stored NLP-4 link.
- **Root cause / layer:** Over-broad token grammar; `URL_NORMALIZATION`.
- **General fix proposal:** Centralize conservative HTTP(S)/`www` extraction and canonicalization, permit valid ASCII path/query/fragment characters, stop at non-ASCII adjacent script, strip surrounding punctuation, and dedupe canonical URLs.
- **Potential files affected:** validation normalizers, baseline/contextual extractors, tests.
- **Regression risk:** Medium for internationalized URLs; IDN scope will remain explicit and conservative rather than silently mutating.
- **Code / annotation / schema:** Code must change; affected URL/evidence candidates may change; no schema change.
- **Tests required:** Indic suffix, separated conjunction, punctuation, valid path/query.
- **Status:** CONFIRMED — PLANNED.

## Issue 14 — URL purpose-sensitive provenance

- **Observed symptom:** A valid occurrence of the same URL can cite the wrong relation.
- **Authoritative source evidence:** SCERT p.3/b2 is application-link context while p.3/b7 is result context for the same SCERT host. KVS p.2/b12 labels two registration URLs by programme.
- **Current code path:** baseline link typing/dedupe, contextual link dedupe, QA `_url`, citation metrics.
- **Current behavior:** URL-only dedupe drops role occurrences; QA accepts first portal/first link; reference validity is mistaken for semantic support.
- **Reproduction status:** Confirmed by code and `hi-q06` evidence mismatch.
- **Root cause / layer:** Relation and scope are absent from dedupe/selection keys; `URL_NORMALIZATION`, `NLP5_STRUCTURED_QA`, `NLP5_CITATION_VALIDATION`.
- **General fix proposal:** Infer link purpose and local scope from source clause, preserve same URL under distinct purposes where needed, select application evidence only for application questions, and add a separate semantic-support metric.
- **Potential files affected:** baseline/contextual extractors, QA service/validation/metrics, tests.
- **Regression risk:** Medium due to historical URL dedupe assumptions.
- **Code / annotation / schema:** Code and `hi-q06` annotation candidate must change; no schema change.
- **Tests required:** Same URL in result/application clauses and purpose-specific citation.
- **Status:** CONFIRMED — PLANNED.

## Issue 15 — Title selection

- **Observed symptom:** Generic `NOTICE` wins over a nearby descriptive heading.
- **Authoritative source evidence:** KVS p.1/b0 is `NOTICE`; p.1/b1-b2 is the descriptive admission-schedule title.
- **Current code path:** baseline `_metadata` first-match/longest-line logic and NLP-4 deterministic title retention.
- **Current behavior:** The first notice-like line becomes title.
- **Reproduction status:** Confirmed in current NLP-4 artifact.
- **Root cause / layer:** No specificity ranking; `NLP2_BASELINE`, `NLP4_RECONCILIATION`.
- **General fix proposal:** Rank early-page title candidates using position, generic-heading penalty, topic/organization specificity, bounded length, and evidence; combine adjacent heading blocks without simply choosing the longest line.
- **Potential files affected:** baseline extractor, NLP-4 reconciliation, tests.
- **Regression risk:** Medium for decorative headers.
- **Code / annotation / schema:** Code and `te-q13` candidate must change; no schema change.
- **Tests required:** Generic heading plus specific title and unrelated long body line.
- **Status:** CONFIRMED — PLANNED.

## Issue 16 — SCERT eligibility completeness

- **Observed symptom:** Current hybrid AST contains only marks and income.
- **Authoritative source evidence:** SCERT p.2/b20-b28 states current government/aided school, Class VII from government/aided school with 55%, income `< 350000`, one attempt, Class VIII non-failure, and excluded KV/JNV/KGBV/residential/private schools.
- **Current code path:** NLP-2 `_eligibility`, NLP-4 `SemanticRuleExtractor`, contextual support, and whole-AST merge.
- **Current behavior:** Numeric rules survive; nonnumeric class/school/attempt/exclusion rules disappear.
- **Reproduction status:** Confirmed from PDF and current NLP-4 AST.
- **Root cause / layer:** Limited controlled vocabulary and parsers plus coarse reconciliation; `CANONICAL_VOCABULARY`, `NLP2_BASELINE`, `NLP4_SEMANTIC_SUPPORT`, `NLP4_RECONCILIATION`.
- **General fix proposal:** Add only source-justified controlled attributes and bounded multilingual patterns, represent exclusions with existing comparators, and allow supported novel conditions to merge.
- **Potential files affected:** semantic rules/support/canonical/extractor, evaluator docs/tests.
- **Regression risk:** High; logical structure and OCR variants require conservative acceptance.
- **Code / annotation / schema:** Code and eligibility QA candidates must change; canonical shape must not.
- **Tests required:** School set, prior class/school, current class, attempt count, exclusions, missing-profile UNKNOWN.
- **Status:** CONFIRMED — PLANNED.

## Issue 17 — Controlled eligibility vocabulary

- **Observed symptom:** There is no documented/supportable vocabulary for source-backed nonnumeric rules.
- **Authoritative source evidence:** SCERT concepts justify `current_class`, `current_school_type`, `previous_class`, `previous_school_type`, `attempt_count`, and `selection_status`; existing attributes cover state/category/disability/marks/income.
- **Current code path:** free-string `Condition.attribute`, support cue map, rule extractors, deterministic evaluator.
- **Current behavior:** Flexible schema permits attributes but support policy rejects unknown ones and extraction omits them.
- **Reproduction status:** Confirmed.
- **Root cause / layer:** Operational vocabulary is narrower than frozen schema capacity; `CANONICAL_VOCABULARY`.
- **General fix proposal:** Document definitions, source wording, normalization, institution values, and evaluator semantics; normalize Roman/numeric class values and institution aliases conservatively.
- **Potential files affected:** semantic rules/support, docs/data contracts, tests.
- **Regression risk:** Medium; synonym normalization must not broaden beyond evidence.
- **Code / annotation / schema:** Code/docs must change; QA candidates may change; no structural schema change.
- **Tests required:** One evaluator/extraction/support case per added attribute/value family.
- **Status:** CONFIRMED — PLANNED.

## Issue 18 — Eligibility exclusions

- **Observed symptom:** Explicit excluded school types are absent from the AST.
- **Authoritative source evidence:** SCERT p.2/b27-b28 excludes KV, JNV, KGBV, residential, and private school students.
- **Current code path:** semantic rules/support/evaluator.
- **Current behavior:** No school-type extraction; existing `NOT_IN` can evaluate the rule but is unused.
- **Reproduction status:** Confirmed; schema capability disproves any need for a new exclusion field.
- **Root cause / layer:** Missing parser/support vocabulary; `CANONICAL_VOCABULARY`, `NLP4_SEMANTIC_SUPPORT`.
- **General fix proposal:** Use `current_school_type NOT_IN [...]` or a logically equivalent supported allowed-set rule; never invent an `excluded_school` boolean.
- **Potential files affected:** semantic rules/support and tests.
- **Regression risk:** Medium where “except” describes a different clause.
- **Code / annotation / schema:** Code must change; schema must not; QA eligibility expectations may change.
- **Tests required:** Allowed school pass, excluded school fail, missing school UNKNOWN.
- **Status:** CONFIRMED — PLANNED.

## Issue 19 — Eligibility AST reconciliation

- **Observed symptom:** Any overlapping attribute causes the entire contextual AST to be rejected.
- **Authoritative source evidence:** Stored SCERT contextual output contains overlapping numeric and additional source-backed concepts; current NLP-4 only retains the deterministic numeric AST.
- **Current code path:** `EvidenceGatedSemanticExtractor._merge_contextual`.
- **Current behavior:** Attribute-set overlap is treated as whole-tree conflict.
- **Reproduction status:** Confirmed by code and diagnostics.
- **Root cause / layer:** Array/tree-level conflict policy instead of atomic/subtree reconciliation; `NLP4_RECONCILIATION`.
- **General fix proposal:** Recursively validate and reconcile atomic conditions, recognize semantic duplicates independent of order/evidence IDs, retain supported novel siblings without flattening nested OR, and isolate true same-attribute conflicts.
- **Potential files affected:** semantic canonical/support/extractor and metrics/tests.
- **Regression risk:** High; preserve guards, evidence, nesting, and deterministic precedence.
- **Code / annotation / schema:** Code must change; annotations need not encode runtime expectations; no schema change.
- **Tests required:** Commutative siblings, non-equivalent nesting, duplicate+novel, threshold conflict, duplicate evidence merge, guarded versus unguarded.
- **Status:** CONFIRMED — PLANNED.

## Issue 20 — Strong-field item reconciliation

- **Observed symptom:** NLP-4 records conflicts for entire dates/fees/links/category arrays rather than reconciling supported items.
- **Authoritative source evidence:** Both notices contain multiple legitimate dates and links; SCERT contextual output also contains unsupported null dates/fees.
- **Current code path:** `_record_strong_field_conflicts`.
- **Current behavior:** Deterministic arrays are retained wholesale and all different contextual arrays rejected as one conflict.
- **Reproduction status:** Confirmed by code.
- **Root cause / layer:** Coarse collection comparison; `NLP4_RECONCILIATION`.
- **General fix proposal:** Field-specific keys and gates: date value/time then role, fee amount/context, normalized URL plus purpose/scope, category document support, and ranked title. Reject unsupported pieces only.
- **Potential files affected:** semantic extractor/support and tests.
- **Regression risk:** High for date-role correction and link-purpose preservation.
- **Code / annotation / schema:** Code must change; candidate citations may change; no schema change.
- **Tests required:** Same date role correction, null date rejection, exact fee precedence, same/different link purposes.
- **Status:** CONFIRMED — PLANNED.

## Issue 21 — Conditional/stage-specific documents

- **Observed symptom:** Conditional and post-selection documents are flattened into universal application requirements.
- **Authoritative source evidence:** SCERT p.2/b10-b12 and p.3/b20-b22 condition caste/disability documents on category/status; p.3/b19 requires income proof only after selection.
- **Current code path:** baseline `_documents` category-only guard, contextual conversion, document dedupe, QA documents.
- **Current behavior:** Broad context and incomplete guards create mandatory/universal documents; stage is not surfaced.
- **Reproduction status:** Confirmed in current NLP-4 document list.
- **Root cause / layer:** Guard recognition is narrow and stage/applicability omitted; `NLP2_BASELINE`, `NLP4_SEMANTIC_SUPPORT`, `NLP5_STRUCTURED_QA`.
- **General fix proposal:** Build existing `applies_when` guards for category, disability, and `selection_status == selected`; preserve stage wording in notes/action association.
- **Potential files affected:** baseline/contextual/semantic extractors, QA service, tests.
- **Regression risk:** Medium; avoid converting consequences into requirements.
- **Code / annotation / schema:** Code and document QA candidates must change; no new stage field/schema change.
- **Tests required:** Category, disability, selected-student, and universal documents.
- **Status:** CONFIRMED — PLANNED.

## Issue 22 — Document deduplication

- **Observed symptom:** Orthographic/translated variants duplicate documents, while semantically different applicability can be collapsed.
- **Authoritative source evidence:** SCERT repeats caste certificate on p.2 and p.3 with equivalent application/category semantics; post-selection income proof has different applicability.
- **Current code path:** contextual `_convert_documents` and NLP-4 `(canonical_name, requirement_type)` key.
- **Current behavior:** Source variants and guards/notes are not jointly considered or merged.
- **Reproduction status:** Confirmed by code/current artifact.
- **Root cause / layer:** Incomplete semantic identity key; `NLP4_RECONCILIATION`.
- **General fix proposal:** Key by normalized canonical identity, requirement type, canonical guard, and represented stage; merge evidence/source variants/notes only for equivalent applicability.
- **Potential files affected:** contextual and semantic extractors/canonical helpers/tests.
- **Regression risk:** Medium.
- **Code / annotation / schema:** Code must change; candidate evidence groups may change; no schema change.
- **Tests required:** Hyphen/spacing/translation duplicate and same document under distinct guards.
- **Status:** CONFIRMED — PLANNED.

## Issue 23 — Preference versus mandatory

- **Observed symptom:** A preference cue can suppress all eligibility semantics in the same block.
- **Authoritative source evidence:** KVS p.2/b12 has transfer-based preference, not mandatory eligibility; synthetic compound clauses establish the general failure mode.
- **Current code path:** `SemanticRuleExtractor.extract` early `continue` and `condition_support` whole-evidence `_PREFERENCE` rejection.
- **Current behavior:** Any preference token rejects the block/condition even if another clause states a mandatory requirement.
- **Reproduction status:** Confirmed by code; not asserted as a current real-fixture mandatory-rule loss without clause evidence.
- **Root cause / layer:** Block-level rather than clause-local cue scope; `NLP4_SEMANTIC_SUPPORT`.
- **General fix proposal:** Split bounded clauses and apply preference suppression only to the clause containing the cue.
- **Potential files affected:** semantic rules/support and tests.
- **Regression risk:** Medium for punctuation-poor OCR.
- **Code / annotation / schema:** Code must change; current KVS preference candidate remains retrieval information; no schema change.
- **Tests required:** Preference experience plus required degree in one block.
- **Status:** CONFIRMED GENERIC DEFECT — PLANNED.

## Issue 24 — Action extraction and association

- **Observed symptom:** Same-type actions collapse, uploads link every document, URLs default to the first, actor responsibility can become applicant action, and translated repeats duplicate workflows.
- **Authoritative source evidence:** SCERT p.3 separates applicant application, selected-student NSP/income steps, and school/district verification responsibilities; KVS p.2 has programme-specific registration links.
- **Current code path:** baseline `_actions`, contextual `_convert_actions`, semantic `_actions`, NLP-4 `_action_key`.
- **Current behavior:** Baseline `seen: set[ActionType]`; global first link/all docs association; descriptions are whole blocks.
- **Reproduction status:** Confirmed by code/current artifacts.
- **Root cause / layer:** Type-level identity and nonlocal association; `ACTION_MODELING`, `NLP2_BASELINE`, `NLP4_RECONCILIATION`.
- **General fix proposal:** Create clause-local action instances keyed by type+object+channel+URL+deadline+guard; attach only local documents/links; retain actor/stage in notes/description; semantic-dedupe translations conservatively.
- **Potential files affected:** baseline/contextual/semantic extractors, QA procedure, metrics/tests.
- **Regression risk:** High; graph dependencies must remain valid.
- **Code / annotation / schema:** Code and procedure candidates must change; no schema change.
- **Tests required:** Two uploads for different documents, local URLs, non-applicant responsibility, translation duplicate, guard/deadline association.
- **Status:** CONFIRMED — PLANNED.

## Issue 25 — NLP-5 title routing

- **Observed symptom:** Title questions fall through to lexical retrieval.
- **Authoritative source evidence:** KVS has structured descriptive title evidence p.1/b1-b2.
- **Current code path:** `QuestionIntent`, router rules, `GroundedQAService.answer` handlers.
- **Current behavior:** No TITLE intent/handler.
- **Reproduction status:** Confirmed by code.
- **Root cause / layer:** Missing structured route; `NLP5_ROUTER`, `NLP5_STRUCTURED_QA`.
- **General fix proposal:** Add a service-layer TITLE intent and multilingual patterns; answer from `metadata.title` with its evidence.
- **Potential files affected:** QA types/router/service/tests.
- **Regression risk:** Low.
- **Code / annotation / schema:** Code and `te-q13` candidate must change; canonical schema does not.
- **Tests required:** English/Hindi/Telugu title questions and absent title.
- **Status:** CONFIRMED — PLANNED.

## Issue 26 — Compound question routing

- **Observed symptom:** “When and where should I apply?” routes only to URL and loses the deadline.
- **Authoritative source evidence:** KVS p.1/b5 deadline and p.1/b6 online-only channel, with p.2/b12 portals.
- **Current code path:** `QuestionRoute` has only venue/date flags; router early returns; service dispatches one handler.
- **Current behavior:** Application-where early return omits `asks_date`; no composed response.
- **Reproduction status:** Confirmed by code.
- **Root cause / layer:** Single-intent early ordering; `NLP5_ROUTER`, `NLP5_STRUCTURED_QA`.
- **General fix proposal:** Preserve component flags and compose bounded date+channel/link, date+venue, and procedure+deadline answers internally.
- **Potential files affected:** QA types/router/service/tests.
- **Regression risk:** Medium for multilingual conjunctions.
- **Code / annotation / schema:** Code and `te-q14` candidate must change; no canonical schema change.
- **Tests required:** Online deadline+where, date+venue partial, procedure+deadline.
- **Status:** CONFIRMED — PLANNED.

## Issue 27 — Channel-aware “where”

- **Observed symptom:** Application location is treated as URL/physical venue rather than channel semantics.
- **Authoritative source evidence:** KVS p.1/b6 explicitly says online only; p.2/b12 supplies portals.
- **Current code path:** router `_url` route and QA `_url` handler.
- **Current behavior:** QA returns one link and ignores canonical action channel; absence of physical address can be misreported partial.
- **Reproduction status:** Confirmed by code and `te-q14` candidate.
- **Root cause / layer:** No channel-aware composition; `NLP5_STRUCTURED_QA`.
- **General fix proposal:** Prefer applicable application actions/channels, include portal when available, and regard supported online-only mode as a complete “where/how” component.
- **Potential files affected:** QA service/router and tests.
- **Regression risk:** Medium for mixed online/offline modes.
- **Code / annotation / schema:** Code and annotation candidate must change; no schema change.
- **Tests required:** Online portal, email, postal, office, and deadline+online.
- **Status:** CONFIRMED — PLANNED.

## Issue 28 — Multiple application links/programme ambiguity

- **Observed symptom:** Generic application-link QA returns the first link.
- **Authoritative source evidence:** KVS p.2/b12 maps Class I and Balvatika III to different URLs.
- **Current code path:** baseline/contextual link scope, `GroundedQAService._url`.
- **Current behavior:** `next(application_portal)` or `links[0]` silently selects one.
- **Reproduction status:** Confirmed; `te-q05`/`te-q15` are under-specified.
- **Root cause / layer:** Link scope is not used and QA has no ambiguity policy; `NLP5_STRUCTURED_QA`.
- **General fix proposal:** Preserve programme labels in link descriptions, select only when the question names a scope, otherwise return all applicable labelled links and state that they are programme-specific.
- **Potential files affected:** extractors, QA service, annotations/tests.
- **Regression risk:** Medium.
- **Code / annotation / schema:** Code and `te-q05`/`te-q15` candidates must change; no schema change.
- **Tests required:** Two programmes, scoped query, generic query, same URL/different purpose.
- **Status:** CONFIRMED — PLANNED.

## Issue 29 — Required-document QA applicability

- **Observed symptom:** QA lists every canonical document without evaluating guards or distinguishing universal/conditional/stage-specific requirements.
- **Authoritative source evidence:** SCERT documents have category/disability/selection conditions; KVS p.1/b7 enumerates no documents.
- **Current code path:** `GroundedQAService._documents`.
- **Current behavior:** All objects are rendered; candidate profile is ignored; any false extracted object makes the question answerable.
- **Reproduction status:** Confirmed by code/current candidates.
- **Root cause / layer:** Missing applicability evaluation and over-trust in canonical list; `NLP5_STRUCTURED_QA`.
- **General fix proposal:** Evaluate `applies_when` against supplied profile; omit non-applicable, label unknown guards as conditional, keep universal items distinct, and abstain when the notice only refers elsewhere.
- **Potential files affected:** QA service, annotation candidates, tests.
- **Regression risk:** Medium; UNKNOWN guards must not be silently excluded or universalized.
- **Code / annotation / schema:** Code and `hi-q05`/`te-q07` candidates must change; no schema change.
- **Tests required:** Profile-applicable/non-applicable/unknown conditional documents and referral-only notice.
- **Status:** CONFIRMED — PLANNED.

## Cross-cutting corrective work after issues 8–29

The implementation will then address the dependent audit requirements: procedure filtering, `ANSWERABLE`/`PARTIAL`/`UNANSWERABLE` versus eligibility `UNKNOWN`, fee absence versus zero, retrieval sufficiency, citation reference validity versus semantic support, alternative evidence groups, condition-aligned eligibility metrics, action-instance metrics, strict evaluation-only annotation models/adapters, scenario-bound candidate profiles, mixed-language metadata, multi-document evaluation identity, NLP-1 text-quality diagnostics without route changes, review-log updates, preserved before/after artifacts, independent NLP-2/NLP-4/NLP-5 reruns, and final reports. A fresh NLP-3 model run is not planned because prompt/context/generation/chunking are not being changed; stored raw candidates will be revalidated under corrected deterministic rules.

## Change-control and verification gates

- Preserve the checked-in reports under `reports/pre_nlp6/before/` before any evaluator overwrites them; produce after-fix reports separately.
- Add synthetic failing tests before or alongside each general implementation fix and run targeted suites after each subsystem.
- Add a static test proving production modules do not import evaluation annotation/profile files.
- Validate review JSON strongly and keep every AI-assisted item unverified.
- Run repository Python only; finish with full pytest, supported real integrations, NLP-2, NLP-4, NLP-5, `git diff --check`, and `git status --short`.
- If high-risk AST/action reconciliation cannot be made safe with existing schema and tests, leave it explicit as a limitation and return a partial status rather than hardcode or weaken validation.

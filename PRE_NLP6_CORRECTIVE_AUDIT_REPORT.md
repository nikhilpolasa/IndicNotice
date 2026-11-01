# Controlled Pre-NLP-6 Corrective Audit Report

## 1. Final status

**PARTIALLY PASSED — IMPORTANT LIMITATIONS REMAIN**

The root-cause pass is safe and regression-clean, but the real corpus is too
small, all review candidates remain unverified, strong-field reconciliation is
still intentionally conservative, and real action extraction remains noisy.

## 2. Executive summary

The pass corrected general extraction, validation, QA, and evaluation defects
without changing canonical schema `1.0`, importing gold into inference, adding
fixture-specific runtime branches, or starting NLP-6. The decisive real-source
changes are a fuller SCERT eligibility AST, conditional SCERT documents, no
fabricated KVS documents, a descriptive KVS title, and two labelled KVS links.

## 3. Baseline repository state

The clean baseline was commit `82ff9f4`. Before implementation, the complete
suite produced 302 passed, 2 expected opt-in Qwen skips, and 0 failed in 47.43
seconds. `CORRECTIVE_AUDIT_PLAN.md` was the first repository change.

## 4. Environment

All Python commands used `.\.venv\Scripts\python.exe`, Python 3.12.10. The
fresh contextual rerun used the checked-in Qwen3-4B Q4_K_M model and installed
llama.cpp build b11429 on localhost only.

## 5. Source documents audited

The source of truth was the original three-page SCERT Haryana NMMSS 2025-26 PDF
and four-page mixed-language KVS Class I/Balvatika-III 2025-26 PDF. Generated
reports were treated only as implementation evidence.

## 6. Audit methodology

The audit reproduced the baseline, preserved reports, inspected each original
page/block, classified root causes, added general regressions, reran a real
model, regenerated downstream artifacts, and manually compared canonical
outputs to source semantics.

## 7. Anti-hardcoding safeguards

Runtime code contains no document IDs, QA IDs, fixture paths, or expected
answers. A static regression rejects review-dataset paths in runtime NLP code.
URLs are normalized but never externally fetched.

## 8. Root-cause classification table

| Layer | Confirmed defects | Outcome |
|---|---:|---|
| NLP-2 baseline | title, document guards/dedupe, URLs, action locality | corrected generally |
| NLP-3 contract/validation | comparator drift, zero fee, null dates, category/docs | corrected generally |
| NLP-4 semantics | vocabulary, exclusions, AST merge, document/action identity | corrected; conservative limits remain |
| NLP-5 QA | title/compound/channel/link/document/procedure behavior | corrected with regressions |
| Evaluation/data | condition/action metrics, adapters, identity key, metadata | corrected; humans still required |

## 9. Contextual comparator-contract defect

The response grammar had noncanonical `CONTAINS` and omitted `NOT_EXISTS`.
It now derives exactly from `Comparator`, with an equality regression.

## 10. Zero-fee validation defect

Fee zero now requires clause-local fee/charge semantics plus negation in
English, Hindi, or Telugu. Unrelated negation is rejected.

## 11. Null-date validation defect

Contextual date candidates without a value, end value, or time are rejected;
generic headings no longer become typed pseudo-dates.

## 12. Category semantic support

Contextual categories require category-specific evidence cues. The erroneous
SCERT admission candidate is rejected while the deterministic scholarship
category remains.

## 13. Required-document support

Concrete document identity and requirement/submission relations are required.
The KVS “visit website for required documents” referral creates no document.

## 14. Conditional/stage-specific documents

SCERT caste, income, and disability certificates are conditional. Guards use
category, `selection_status == selected`, and disability status respectively.

## 15. Document deduplication

Document identity includes canonical name, requirement type, canonical guard,
alternatives, and notes. Equivalent source variants merge evidence; different
applicability remains distinct.

## 16. URL tokenization

A shared conservative token grammar stops before adjacent Indic text, strips
punctuation, and retains valid ASCII paths, queries, and fragments.

## 17. URL semantic provenance

Links retain purpose and local description. Application QA no longer treats a
results occurrence of the same host as application evidence.

## 18. Title selection

Specificity ranking with a generic-heading penalty combines nearby top-page
headings. KVS now yields its full descriptive admission-schedule title rather
than `NOTICE`.

## 19. Eligibility vocabulary additions

Service-layer vocabulary now covers `current_class`, `current_school_type`,
`previous_class`, `previous_school_type`, `attempt_count`, and
`selection_status`, plus controlled institution-type values. Schema 1.0 did not
change.

## 20. SCERT eligibility completeness

The after AST has eight source-backed leaves: marks, current class/current
school type, previous class/previous school type, income, attempt count, and
school-type exclusions. The explicit Class-VIII failure rule is not yet a
separate leaf and is documented as a limitation.

## 21. Eligibility AST merge

Supported novel children of AND groups can survive duplicate/conflicting
siblings. OR and guarded subtrees remain atomic where partial removal would
change logic.

## 22. Strong-field item reconciliation

Unsupported contextual items are validated and rejected individually before
deterministic precedence is recorded. Full bidirectional item merging for every
date/fee/link role remains conservatively deferred.

## 23. Action extraction/association

Repeated action types are preserved and local documents/URLs are associated.
Third-party responsibility is filtered. Real SCERT OCR still produces noisy
upload repetitions, so this area is improved but not complete.

## 24. QA title routing

English, Hindi, and Telugu title questions route to structured metadata.

## 25. Compound/channel QA

Date+venue and deadline+channel questions preserve supported components.
Application “where” recognizes online channel rather than assuming a venue.

## 26. Multiple-link handling

Unscoped KVS registration questions return both labelled Class I and
Balvatika-III links; programme-scoped questions select the matching link.

## 27. Required-document QA

Document guards are evaluated against candidate profiles. Inapplicable items
are omitted and unknown conditional applicability is labelled. KVS document QA
abstains because the notice enumerates no concrete documents.

## 28. Procedure QA

Procedure answers filter to applicant-relevant application actions and profile
guards instead of emitting every actor's workflow.

## 29. Answerability / UNKNOWN distinction

Notice-level absence produces UNANSWERABLE/NOT_STATED. Missing candidate fields
produce PARTIAL with deterministic eligibility `UNKNOWN` and named missing
attributes.

## 30. Retrieval answerability

A lexical match is not treated as sufficient proof of the requested relation.
Structured fields and bounded relation checks take precedence; unsupported
questions abstain.

## 31. Citation reference validity

Citation validity remains the mechanical check that the evidence reference
exists in the same document.

## 32. Citation semantic support

A separate metric checks critical tokens and relation cues. A valid result-URL
citation cannot support an application-link answer.

## 33. Eligibility metric correction

Conditions align by attribute/instance before operator and value scoring. The
adversarial swapped-value case now receives zero operator/value accuracy.

## 34. Action metric correction

Action and edge scoring uses multisets of action instances. Predicting one of
two uploads has recall 0.5 rather than collapsing to a perfect type match.

## 35. NLP-4 executable semantic review data

Strict models load all 20 semantic records and deterministically adapt them to
canonical evidence and candidates. Unresolved relaxation/exemption/preference
concepts remain explicit rather than fabricated as facts.

## 36. Candidate-profile scenario binding

Thirteen profiles now reference seven explicit canonical AST scenarios. All
expected PASS/FAIL/UNKNOWN/NOT_APPLICABLE results execute successfully.

## 37. Mixed-language evaluation metadata

The QA annotation contract accepts `mixed`, and all KVS QA candidates are
labelled mixed instead of Telugu-only.

## 38. NLP-5 multi-document evaluation fix

Evaluation records key by `document_id`, reject duplicate IDs, and accept
isolated `--input`/`--output` paths. A regression preserves two Hindi and two
Telugu notices without overwrite.

## 39. NLP-1 text-quality limitation

Non-routing diagnostics now expose replacement-character rate, suspicious
mojibake markers, alphanumeric density, dominant-script consistency, and URL
corruption. They do not silently repair or reroute extraction.

## 40. Dataset-size / language-composition limitations

The real NLP-3/4/5 support N is two notices: one Hindi notice and one mixed
English/Hindi/Telugu notice. No statistical significance, broad language
quality, or production readiness is claimed.

## 41. Annotation candidate corrections

All 30 QA items gained explicit real-notice scope; 15 KVS items gained mixed
language metadata. Source-corrected candidates cover SCERT documents, URLs,
eligibility, procedure, exam details, ambiguous marks, and KVS links,
documents, title, and application channel. Every item remains
`NEEDS_HUMAN_VERIFICATION`; details are in `docs/NLP6_PREP_REVIEW_LOG.md`.

## 42. Tests added

Thirty-six net new tests cover comparator synchronization, multilingual fee
negation, null dates, category/document semantics, URLs/titles/actions,
eligibility vocabulary/merging/metrics, QA routing/applicability/link scope,
review adapters, scenario fixtures, text diagnostics, evaluation identity, and
gold-leakage safeguards.

## 43. Regression results

Final suite: **338 passed, 2 expected opt-in Qwen skips, 0 failed in 102.13s**.
The same run covered both NLP-1 real fixtures, NLP-2 real documents, and both
NLP-5 real QA integrations.

## 44. NLP-2 before/after integrity

NLP-2 remains independently runnable. Its rerun evaluated six documents with
category, fee, and notice-number F1/exact match 1.0 and explicitly skipped four
OCR-required fixtures. Behavior changes are explainable: descriptive title,
safer URLs, local action instances, and applicability-aware documents.

## 45. NLP-3 before/after integrity

A fresh real Qwen run occurred; no stale cached output was substituted. It
produced schema-valid outputs and 63/63 valid evidence references after 11
repair attempts. Category F1 remained 0.5 and fee F1 remained 0.0. Grounding
diagnostics reported many unsupported/hallucinated candidates, so NLP-3 remains
experimental and independently defined.

## 46. NLP-4 before/after behavior

Before: 9 contextual candidates promoted, 17 rejected. After the fresh model
run: 0 promoted, 23 rejected. This count is not an accuracy claim: stricter
support gates rejected the fresh model's unsupported candidates, while general
deterministic semantic rules supplied the source-backed SCERT AST and document
guards. KVS documents are empty; KVS title and links are correct.

## 47. NLP-5 before/after behavior

Both smoke runs have eight cases, eight valid citation-reference cases, and two
abstentions. The important semantic change is SCERT sparse eligibility:
marks+income now returns UNKNOWN with five missing source-derived fields, and
marks-only returns six. Targeted tests cover title, documents, links, compound
questions, and semantic citation support beyond the eight-case smoke.

## 48. Remaining limitations

Human verification is outstanding; corpus size is tiny; SCERT OCR is noisy;
the Class-VIII failure rule is not separately represented; some excluded
institution variants are missed; action extraction remains repetitive; open
retrieval support is bounded; and strong-field reconciliation remains
conservative.

## 49. Deferred post-freeze schema ideas

Potential future migrations include K-of-N documents, explicit temporal stage,
typed programme scope, and richer URL-purpose relations. None was added to
schema `1.0`.

## 50. Data-gap recommendations

Add independently sourced native/scanned Hindi, Telugu, and genuinely mixed
notices across notice types, with fee absence/zero, conditional documents,
nested eligibility, multiple URLs, multiple same-language documents, compound
QA, and wrong-relation citation adversaries. See
`docs/NLP6_DATA_GAP_PLAN.md`.

## 51. Readiness for final human verification

The typed corpora load, source corrections are logged, and all candidates are
still unverified. Most items are **READY_FOR_HUMAN_REVIEW**; `hi-q15` remains
**REMAINS_AMBIGUOUS** because “minimum marks” can mean prior-class eligibility
or MAT/SAT qualifying marks. No item is claimed human-verified.

## 52. Recommendation on NLP-6 readiness

**READY FOR FINAL HUMAN REVIEW**, but **not ready to start NLP-6** until that
review resolves ambiguity and verifies the candidate sets. NLP-6 was not
started, and no commit was created.

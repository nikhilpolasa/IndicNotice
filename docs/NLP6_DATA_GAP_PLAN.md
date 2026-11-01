# NLP-6 Data-Gap Plan

This plan is for later human-reviewed evaluation design. It does not start
NLP-6 and does not promote current candidates to gold.

## Current support and limits

The real corrective corpus contains one Hindi SCERT scholarship notice and one
mixed English/Hindi/Telugu KVS admission notice. Support N is therefore two
notices, not a statistically meaningful language benchmark. The NLP-4 semantic
review set has 20 synthetic candidates; the NLP-5 review set has 30 real-notice
question candidates. All remain `NEEDS_HUMAN_VERIFICATION`.

## Priority additions

1. Add at least three independently sourced notices per notice type and script:
   native Hindi, native Telugu, scanned Hindi, scanned Telugu, and genuinely
   mixed-language layouts.
2. Add notices with explicit no-fee, fee-not-stated, waived-category fee, and
   unrelated negation examples.
3. Add document policies covering mandatory, optional, category-conditional,
   disability-conditional, post-selection, alternatives, and referral-only
   wording.
4. Add eligibility ASTs with exclusions, one-attempt rules, school history,
   class history, guarded relaxations, nested AND/OR logic, and genuine
   ambiguity.
5. Add notices containing multiple same-purpose and different-purpose URLs,
   Unicode immediately after URLs, query strings, fragments, and wrapped URLs.
6. Add multiple notices in the same language to exercise document identity and
   prevent evaluation overwrite.
7. Add compound QA cases for date+venue, deadline+channel, procedure+documents,
   programme-scoped links, notice-level unanswerable questions, and
   candidate-level unknown eligibility.
8. Add adversarial citation cases where the evidence ID is valid but supports a
   different relation (results URL versus application URL, document mention
   versus submission obligation).

## Human review protocol

Two reviewers should independently inspect the original page and record answer,
answerability, exact/acceptable evidence groups, scope, and ambiguity. Resolve
disagreements with a third adjudication record. Preserve review history and
report agreement with support N. Never use the held-out annotations during
runtime extraction, retrieval, routing, or answer generation.

## Deferred schema ideas

K-of-N document requirements, richer temporal stages, explicit programme scope,
and typed URL-purpose relations may justify a future schema migration. They are
not silently added to schema `1.0` in this corrective pass.

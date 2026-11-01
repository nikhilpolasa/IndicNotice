# Final Human Review Package

Status: **HUMAN GOLD GATE: OPEN**

This package is a review aid, not gold and not an evaluation report. No item was
marked `VERIFIED` by automation, and final NLP-6 scoring has not started.

## Contents

- `qa_review.md`: all 30 real-notice QA candidates with source evidence.
- `semantic_review.md`: all 20 synthetic semantic challenge cases.
- `profile_review.md`: all 13 synthetic evaluator scenarios, executed from AST + profile.
- `review_summary.json`: machine-readable counts and AI audit suggestions.

## Required review procedure

1. Open the source PDF named in each QA record at the listed page; the PDF is authoritative.
2. Decide each QA item explicitly: verify, correct, exclude, or leave unverified.
3. Exclude `hi-q15` from final scored gold because the current question has multiple valid interpretations. Do not rewrite it into an easier scored item.
4. Review every synthetic semantic case separately; do not describe these as real-notice gold.
5. Review the candidate-profile expectations and any boundary/missing-information behavior.
6. Apply decisions manually or with `scripts/review_final_annotations.py`.
7. Create a manifest only after the intended selected items are `VERIFIED`, then run `scripts/validate_nlp6_gold.py`.

`READY_TO_VERIFY` is only AI guidance. It never means `VERIFIED`.

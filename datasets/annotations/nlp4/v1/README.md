# NLP-4 semantic review set v1

This directory contains agent-prepared, manually reviewable Hindi and Telugu
eligibility/action examples. Every item is explicitly
`NEEDS_HUMAN_VERIFICATION`; none is gold and none is included in scored
results. `schema.json` documents the review contract. A reviewer must compare
the candidate structure with the preserved source text before changing
`verification_state` to `VERIFIED`.

Real-document execution is reported separately in
`reports/nlp4_real_evaluation.json`. Only fields already marked
`verified_complete` in the NLP-2 annotation set are scored there.

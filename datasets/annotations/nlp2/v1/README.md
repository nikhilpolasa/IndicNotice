# NLP-2 gold annotations, version 1

`annotations.json` is deliberately honest about review coverage. Only a field
whose status is `verified_complete` may enter precision, recall, F1 or exact
match calculations. `verified_partial` is useful for regression spot checks
but cannot establish false positives. `unverified` and `template_only` are not
gold.

Verification was manual against the named official PDF and its cited page or
source excerpt. No label was filled from extractor output. The initial corpus
therefore contains complete category labels and a small number of complete
identity/fee labels, while complex dates, eligibility and procedures remain
partial until a second annotation pass.

Statuses:

- `verified_complete`: exhaustive for that field in the document; scoreable.
- `verified_partial`: checked labels, but not claimed exhaustive; not scoreable.
- `unverified`: candidate annotation awaiting review; not scoreable.
- `template_only`: fixture registered with no field claim; not scoreable.

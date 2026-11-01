# Candidate-Profile Scenario Review

> These are 13 synthetic deterministic-evaluator cases. Actual results below are computed from each canonical AST plus its candidate profile; stored expectations are used only for comparison.

## clear-pass

- Linked scenario: `numeric-core` — Age, marks, and annual-family-income requirements combined with AND.
- Expected result: `PASS`
- Actual deterministic result: `PASS`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator
  - marks_percentage >= 75: inclusive lower comparator
  - annual_family_income_inr <= 300000: inclusive upper comparator
- Candidate attributes:
```json
{
  "age": 24,
  "marks_percentage": 80,
  "annual_family_income_inr": 200000,
  "category": "GENERAL"
}
```
- Evaluated AST:
```json
{
  "group_id": "numeric-core",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "age-max",
      "attribute": "age",
      "comparator": "<=",
      "value": 30,
      "unit": "years",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    },
    {
      "condition_id": "marks-min",
      "attribute": "marks_percentage",
      "comparator": ">=",
      "value": 75,
      "unit": "%",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    },
    {
      "condition_id": "income-max",
      "attribute": "annual_family_income_inr",
      "comparator": "<=",
      "value": 300000,
      "unit": "INR",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "age-max",
    "status": "PASS",
    "reason": "'age' <= 30 years: candidate has 24 → PASS"
  },
  {
    "condition_id": "marks-min",
    "status": "PASS",
    "reason": "'marks_percentage' >= 75 %: candidate has 80 → PASS"
  },
  {
    "condition_id": "income-max",
    "status": "PASS",
    "reason": "'annual_family_income_inr' <= 300000 INR: candidate has 200000 → PASS"
  }
]
```

## clear-fail

- Linked scenario: `numeric-core` — Age, marks, and annual-family-income requirements combined with AND.
- Expected result: `FAIL`
- Actual deterministic result: `FAIL`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator
  - marks_percentage >= 75: inclusive lower comparator
  - annual_family_income_inr <= 300000: inclusive upper comparator
- Candidate attributes:
```json
{
  "age": 31,
  "marks_percentage": 70,
  "annual_family_income_inr": 400000,
  "category": "GENERAL"
}
```
- Evaluated AST:
```json
{
  "group_id": "numeric-core",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "age-max",
      "attribute": "age",
      "comparator": "<=",
      "value": 30,
      "unit": "years",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    },
    {
      "condition_id": "marks-min",
      "attribute": "marks_percentage",
      "comparator": ">=",
      "value": 75,
      "unit": "%",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    },
    {
      "condition_id": "income-max",
      "attribute": "annual_family_income_inr",
      "comparator": "<=",
      "value": 300000,
      "unit": "INR",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "age-max",
    "status": "FAIL",
    "reason": "'age' <= 30 years: candidate has 31 → FAIL"
  },
  {
    "condition_id": "marks-min",
    "status": "FAIL",
    "reason": "'marks_percentage' >= 75 %: candidate has 70 → FAIL"
  },
  {
    "condition_id": "income-max",
    "status": "FAIL",
    "reason": "'annual_family_income_inr' <= 300000 INR: candidate has 400000 → FAIL"
  }
]
```

## income-missing

- Linked scenario: `numeric-core` — Age, marks, and annual-family-income requirements combined with AND.
- Expected result: `UNKNOWN`
- Actual deterministic result: `UNKNOWN`
- PASS/FAIL consistency: `True`
- Missing information: `annual_family_income_inr`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator
  - marks_percentage >= 75: inclusive lower comparator
  - annual_family_income_inr <= 300000: inclusive upper comparator
- Candidate attributes:
```json
{
  "age": 24,
  "marks_percentage": 80
}
```
- Evaluated AST:
```json
{
  "group_id": "numeric-core",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "age-max",
      "attribute": "age",
      "comparator": "<=",
      "value": 30,
      "unit": "years",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    },
    {
      "condition_id": "marks-min",
      "attribute": "marks_percentage",
      "comparator": ">=",
      "value": 75,
      "unit": "%",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    },
    {
      "condition_id": "income-max",
      "attribute": "annual_family_income_inr",
      "comparator": "<=",
      "value": 300000,
      "unit": "INR",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "age-max",
    "status": "PASS",
    "reason": "'age' <= 30 years: candidate has 24 → PASS"
  },
  {
    "condition_id": "marks-min",
    "status": "PASS",
    "reason": "'marks_percentage' >= 75 %: candidate has 80 → PASS"
  },
  {
    "condition_id": "income-max",
    "status": "UNKNOWN",
    "reason": "Attribute 'annual_family_income_inr' not in candidate profile; cannot evaluate <= 300000"
  }
]
```

## sc-relaxation

- Linked scenario: `category-age-relaxation` — General candidates have age 30; SC/ST candidates have age 35.
- Expected result: `PASS`
- Actual deterministic result: `PASS`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator
  - category NOT_IN ['SC', 'ST']: non-ordered comparator
  - age <= 35: inclusive upper comparator
  - category IN ['SC', 'ST']: non-ordered comparator
- Candidate attributes:
```json
{
  "age": 33,
  "category": "SC"
}
```
- Evaluated AST:
```json
{
  "group_id": "age-relaxation",
  "operator": "OR",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "group_id": "general",
      "operator": "AND",
      "label": null,
      "applies_when": {
        "group_id": "general-guard",
        "operator": "AND",
        "label": null,
        "applies_when": null,
        "children": [
          {
            "condition_id": "general-category",
            "attribute": "category",
            "comparator": "NOT_IN",
            "value": [
              "SC",
              "ST"
            ],
            "unit": null,
            "negated": false,
            "scope": null,
            "exception_of": null,
            "applies_when": null,
            "reference_date": null,
            "source_text": null,
            "evidence_ids": [],
            "confidence": 1.0,
            "review_state": "auto_extracted"
          }
        ],
        "evidence_ids": []
      },
      "children": [
        {
          "condition_id": "general-age",
          "attribute": "age",
          "comparator": "<=",
          "value": 30,
          "unit": "years",
          "negated": false,
          "scope": null,
          "exception_of": null,
          "applies_when": null,
          "reference_date": null,
          "source_text": null,
          "evidence_ids": [],
          "confidence": 1.0,
          "review_state": "auto_extracted"
        }
      ],
      "evidence_ids": []
    },
    {
      "group_id": "reserved",
      "operator": "AND",
      "label": null,
      "applies_when": {
        "group_id": "reserved-guard",
        "operator": "AND",
        "label": null,
        "applies_when": null,
        "children": [
          {
            "condition_id": "reserved-category",
            "attribute": "category",
            "comparator": "IN",
            "value": [
              "SC",
              "ST"
            ],
            "unit": null,
            "negated": false,
            "scope": null,
            "exception_of": null,
            "applies_when": null,
            "reference_date": null,
            "source_text": null,
            "evidence_ids": [],
            "confidence": 1.0,
            "review_state": "auto_extracted"
          }
        ],
        "evidence_ids": []
      },
      "children": [
        {
          "condition_id": "reserved-age",
          "attribute": "age",
          "comparator": "<=",
          "value": 35,
          "unit": "years",
          "negated": false,
          "scope": null,
          "exception_of": null,
          "applies_when": null,
          "reference_date": null,
          "source_text": null,
          "evidence_ids": [],
          "confidence": 1.0,
          "review_state": "auto_extracted"
        }
      ],
      "evidence_ids": []
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "reserved-age",
    "status": "PASS",
    "reason": "'age' <= 35 years: candidate has 33 → PASS"
  }
]
```

## general-no-relaxation

- Linked scenario: `category-age-relaxation` — General candidates have age 30; SC/ST candidates have age 35.
- Expected result: `FAIL`
- Actual deterministic result: `FAIL`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator
  - category NOT_IN ['SC', 'ST']: non-ordered comparator
  - age <= 35: inclusive upper comparator
  - category IN ['SC', 'ST']: non-ordered comparator
- Candidate attributes:
```json
{
  "age": 33,
  "category": "GENERAL"
}
```
- Evaluated AST:
```json
{
  "group_id": "age-relaxation",
  "operator": "OR",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "group_id": "general",
      "operator": "AND",
      "label": null,
      "applies_when": {
        "group_id": "general-guard",
        "operator": "AND",
        "label": null,
        "applies_when": null,
        "children": [
          {
            "condition_id": "general-category",
            "attribute": "category",
            "comparator": "NOT_IN",
            "value": [
              "SC",
              "ST"
            ],
            "unit": null,
            "negated": false,
            "scope": null,
            "exception_of": null,
            "applies_when": null,
            "reference_date": null,
            "source_text": null,
            "evidence_ids": [],
            "confidence": 1.0,
            "review_state": "auto_extracted"
          }
        ],
        "evidence_ids": []
      },
      "children": [
        {
          "condition_id": "general-age",
          "attribute": "age",
          "comparator": "<=",
          "value": 30,
          "unit": "years",
          "negated": false,
          "scope": null,
          "exception_of": null,
          "applies_when": null,
          "reference_date": null,
          "source_text": null,
          "evidence_ids": [],
          "confidence": 1.0,
          "review_state": "auto_extracted"
        }
      ],
      "evidence_ids": []
    },
    {
      "group_id": "reserved",
      "operator": "AND",
      "label": null,
      "applies_when": {
        "group_id": "reserved-guard",
        "operator": "AND",
        "label": null,
        "applies_when": null,
        "children": [
          {
            "condition_id": "reserved-category",
            "attribute": "category",
            "comparator": "IN",
            "value": [
              "SC",
              "ST"
            ],
            "unit": null,
            "negated": false,
            "scope": null,
            "exception_of": null,
            "applies_when": null,
            "reference_date": null,
            "source_text": null,
            "evidence_ids": [],
            "confidence": 1.0,
            "review_state": "auto_extracted"
          }
        ],
        "evidence_ids": []
      },
      "children": [
        {
          "condition_id": "reserved-age",
          "attribute": "age",
          "comparator": "<=",
          "value": 35,
          "unit": "years",
          "negated": false,
          "scope": null,
          "exception_of": null,
          "applies_when": null,
          "reference_date": null,
          "source_text": null,
          "evidence_ids": [],
          "confidence": 1.0,
          "review_state": "auto_extracted"
        }
      ],
      "evidence_ids": []
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "general-age",
    "status": "FAIL",
    "reason": "'age' <= 30 years: candidate has 33 → FAIL"
  }
]
```

## category-missing

- Linked scenario: `category-age-relaxation` — General candidates have age 30; SC/ST candidates have age 35.
- Expected result: `UNKNOWN`
- Actual deterministic result: `UNKNOWN`
- PASS/FAIL consistency: `True`
- Missing information: `category`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator
  - category NOT_IN ['SC', 'ST']: non-ordered comparator
  - age <= 35: inclusive upper comparator
  - category IN ['SC', 'ST']: non-ordered comparator
- Candidate attributes:
```json
{
  "age": 33
}
```
- Evaluated AST:
```json
{
  "group_id": "age-relaxation",
  "operator": "OR",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "group_id": "general",
      "operator": "AND",
      "label": null,
      "applies_when": {
        "group_id": "general-guard",
        "operator": "AND",
        "label": null,
        "applies_when": null,
        "children": [
          {
            "condition_id": "general-category",
            "attribute": "category",
            "comparator": "NOT_IN",
            "value": [
              "SC",
              "ST"
            ],
            "unit": null,
            "negated": false,
            "scope": null,
            "exception_of": null,
            "applies_when": null,
            "reference_date": null,
            "source_text": null,
            "evidence_ids": [],
            "confidence": 1.0,
            "review_state": "auto_extracted"
          }
        ],
        "evidence_ids": []
      },
      "children": [
        {
          "condition_id": "general-age",
          "attribute": "age",
          "comparator": "<=",
          "value": 30,
          "unit": "years",
          "negated": false,
          "scope": null,
          "exception_of": null,
          "applies_when": null,
          "reference_date": null,
          "source_text": null,
          "evidence_ids": [],
          "confidence": 1.0,
          "review_state": "auto_extracted"
        }
      ],
      "evidence_ids": []
    },
    {
      "group_id": "reserved",
      "operator": "AND",
      "label": null,
      "applies_when": {
        "group_id": "reserved-guard",
        "operator": "AND",
        "label": null,
        "applies_when": null,
        "children": [
          {
            "condition_id": "reserved-category",
            "attribute": "category",
            "comparator": "IN",
            "value": [
              "SC",
              "ST"
            ],
            "unit": null,
            "negated": false,
            "scope": null,
            "exception_of": null,
            "applies_when": null,
            "reference_date": null,
            "source_text": null,
            "evidence_ids": [],
            "confidence": 1.0,
            "review_state": "auto_extracted"
          }
        ],
        "evidence_ids": []
      },
      "children": [
        {
          "condition_id": "reserved-age",
          "attribute": "age",
          "comparator": "<=",
          "value": 35,
          "unit": "years",
          "negated": false,
          "scope": null,
          "exception_of": null,
          "applies_when": null,
          "reference_date": null,
          "source_text": null,
          "evidence_ids": [],
          "confidence": 1.0,
          "review_state": "auto_extracted"
        }
      ],
      "evidence_ids": []
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[]
```

## pwd-exemption

- Linked scenario: `pwd-age-exemption` — The age rule does not apply to PwD candidates.
- Expected result: `NOT_APPLICABLE`
- Actual deterministic result: `NOT_APPLICABLE`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator
  - disability_status != 'PwD': non-ordered comparator
- Candidate attributes:
```json
{
  "age": 40,
  "disability_status": "PwD"
}
```
- Evaluated AST:
```json
{
  "group_id": "pwd-exemption",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "non-pwd-age",
      "attribute": "age",
      "comparator": "<=",
      "value": 30,
      "unit": "years",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": {
        "group_id": "non-pwd",
        "operator": "AND",
        "label": null,
        "applies_when": null,
        "children": [
          {
            "condition_id": "not-pwd",
            "attribute": "disability_status",
            "comparator": "!=",
            "value": "PwD",
            "unit": null,
            "negated": false,
            "scope": null,
            "exception_of": null,
            "applies_when": null,
            "reference_date": null,
            "source_text": null,
            "evidence_ids": [],
            "confidence": 1.0,
            "review_state": "auto_extracted"
          }
        ],
        "evidence_ids": []
      },
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "non-pwd-age",
    "status": "NOT_APPLICABLE",
    "reason": "Condition 'non-pwd-age' does not apply (guard applies_when not satisfied)"
  }
]
```

## multiple-degrees

- Linked scenario: `degree-alternative` — Either B.Tech or B.E. satisfies the degree requirement.
- Expected result: `PASS`
- Actual deterministic result: `PASS`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - education_level == 'B.Tech': non-ordered comparator
  - education_level == 'B.E.': non-ordered comparator
- Candidate attributes:
```json
{
  "education_level": [
    "B.Sc",
    "B.E."
  ]
}
```
- Evaluated AST:
```json
{
  "group_id": "degree",
  "operator": "OR",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "btech",
      "attribute": "education_level",
      "comparator": "==",
      "value": "B.Tech",
      "unit": null,
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    },
    {
      "condition_id": "be",
      "attribute": "education_level",
      "comparator": "==",
      "value": "B.E.",
      "unit": null,
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "btech",
    "status": "FAIL",
    "reason": "'education_level' == 'B.Tech': candidate has ['B.Sc', 'B.E.'] → FAIL"
  },
  {
    "condition_id": "be",
    "status": "PASS",
    "reason": "'education_level' == 'B.E.': candidate has ['B.Sc', 'B.E.'] → PASS"
  }
]
```

## age-boundary

- Linked scenario: `cutoff-age` — Age is computed from date of birth at the stated cutoff date.
- Expected result: `PASS`
- Actual deterministic result: `PASS`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - age <= 30: inclusive upper comparator at cutoff 2026-07-01
- Candidate attributes:
```json
{
  "date_of_birth": "1996-07-01"
}
```
- Evaluated AST:
```json
{
  "group_id": "cutoff-age",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "cutoff-age-max",
      "attribute": "age",
      "comparator": "<=",
      "value": 30,
      "unit": "years",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": "2026-07-01",
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "cutoff-age-max",
    "status": "PASS",
    "reason": "'age' <= 30 years: candidate has 30 → PASS"
  }
]
```

## income-boundary

- Linked scenario: `income-boundary` — Annual family income is at most INR 250000.
- Expected result: `PASS`
- Actual deterministic result: `PASS`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - annual_family_income_inr <= 250000: inclusive upper comparator
- Candidate attributes:
```json
{
  "annual_family_income_inr": 250000
}
```
- Evaluated AST:
```json
{
  "group_id": "income-boundary",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "income-250k",
      "attribute": "annual_family_income_inr",
      "comparator": "<=",
      "value": 250000,
      "unit": "INR",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "income-250k",
    "status": "PASS",
    "reason": "'annual_family_income_inr' <= 250000 INR: candidate has 250000 → PASS"
  }
]
```

## marks-below

- Linked scenario: `marks-boundary` — Marks percentage is at least 75.
- Expected result: `FAIL`
- Actual deterministic result: `FAIL`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - marks_percentage >= 75: inclusive lower comparator
- Candidate attributes:
```json
{
  "marks_percentage": 74.99
}
```
- Evaluated AST:
```json
{
  "group_id": "marks-boundary",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "marks-75",
      "attribute": "marks_percentage",
      "comparator": ">=",
      "value": 75,
      "unit": "%",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "marks-75",
    "status": "FAIL",
    "reason": "'marks_percentage' >= 75 %: candidate has 74.99 → FAIL"
  }
]
```

## marks-exact

- Linked scenario: `marks-boundary` — Marks percentage is at least 75.
- Expected result: `PASS`
- Actual deterministic result: `PASS`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - marks_percentage >= 75: inclusive lower comparator
- Candidate attributes:
```json
{
  "marks_percentage": 75
}
```
- Evaluated AST:
```json
{
  "group_id": "marks-boundary",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "marks-75",
      "attribute": "marks_percentage",
      "comparator": ">=",
      "value": 75,
      "unit": "%",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "marks-75",
    "status": "PASS",
    "reason": "'marks_percentage' >= 75 %: candidate has 75 → PASS"
  }
]
```

## marks-above

- Linked scenario: `marks-boundary` — Marks percentage is at least 75.
- Expected result: `PASS`
- Actual deterministic result: `PASS`
- PASS/FAIL consistency: `True`
- Missing information: `NONE`
- Expected outcome unambiguous under this AST: `True`
- Boundary / strict-vs-inclusive semantics:
  - marks_percentage >= 75: inclusive lower comparator
- Candidate attributes:
```json
{
  "marks_percentage": 75.01
}
```
- Evaluated AST:
```json
{
  "group_id": "marks-boundary",
  "operator": "AND",
  "label": null,
  "applies_when": null,
  "children": [
    {
      "condition_id": "marks-75",
      "attribute": "marks_percentage",
      "comparator": ">=",
      "value": 75,
      "unit": "%",
      "negated": false,
      "scope": null,
      "exception_of": null,
      "applies_when": null,
      "reference_date": null,
      "source_text": null,
      "evidence_ids": [],
      "confidence": 1.0,
      "review_state": "auto_extracted"
    }
  ],
  "evidence_ids": []
}
```
- Per-condition evaluator output:
```json
[
  {
    "condition_id": "marks-75",
    "status": "PASS",
    "reason": "'marks_percentage' >= 75 %: candidate has 75.01 → PASS"
  }
]
```

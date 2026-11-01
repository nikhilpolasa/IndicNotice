# Synthetic Semantic Human Review

> All 20 records are synthetic semantic challenge cases. They are not real-notice annotations and must never be reported as real-notice gold.

## hi-01

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: अभ्यर्थी की आयु अधिकतम 25 वर्ष होनी चाहिए।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "age",
    "operator": "<=",
    "value": 25,
    "unit": "years",
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## hi-02

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: न्यूनतम आयु 18 वर्ष है।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "age",
    "operator": ">=",
    "value": 18,
    "unit": "years",
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## hi-03

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: परिवार की वार्षिक आय ₹3,00,000 से कम होनी चाहिए।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "annual_family_income_inr",
    "operator": "<",
    "value": 300000,
    "unit": null,
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## hi-04

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: कम से कम 75 प्रतिशत अंक अनिवार्य हैं।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "marks_percentage",
    "operator": ">=",
    "value": 75,
    "unit": null,
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## hi-05

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: B.Tech अथवा B.E. डिग्री होना आवश्यक है।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "education_level",
    "operator": "==",
    "value": "B.Tech",
    "unit": null,
    "reference_date": null
  },
  {
    "attribute": "education_level",
    "operator": "==",
    "value": "B.E.",
    "unit": null,
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[
  {
    "operator": "OR",
    "members": [
      0,
      1
    ],
    "kind": null,
    "attribute": null,
    "delta": null,
    "target": null,
    "unresolved_without_base": null,
    "must_not_be_mandatory": null
  }
]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## hi-06

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `eligibility/semantic-rule + applicability-guard`
- Source sentence: ऊपरी आयु सीमा SC/ST अभ्यर्थियों के लिए 5 वर्ष शिथिल है।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required. Relaxation/exemption/preference metadata is intentionally preserved as an unresolved adapter diagnostic.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[
  {
    "attribute": "category",
    "operator": "IN",
    "value": [
      "SC",
      "ST"
    ],
    "unit": null,
    "reference_date": null
  }
]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[
  {
    "operator": null,
    "members": [],
    "kind": "delta_relaxation",
    "attribute": "age",
    "delta": 5.0,
    "target": null,
    "unresolved_without_base": true,
    "must_not_be_mandatory": null
  }
]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 0,
  "unresolved": [
    "hi-06:delta_relaxation"
  ]
}
```

## hi-07

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `eligibility/semantic-rule + applicability-guard`
- Source sentence: दिव्यांग व्यक्ति आयु आवश्यकता से मुक्त हैं।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required. Relaxation/exemption/preference metadata is intentionally preserved as an unresolved adapter diagnostic.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[
  {
    "attribute": "disability_status",
    "operator": "==",
    "value": "PwD",
    "unit": null,
    "reference_date": null
  }
]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[
  {
    "operator": null,
    "members": [],
    "kind": "exemption",
    "attribute": null,
    "delta": null,
    "target": "age",
    "unresolved_without_base": null,
    "must_not_be_mandatory": null
  }
]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 0,
  "unresolved": [
    "hi-07:exemption"
  ]
}
```

## hi-08

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `applicability-guard + action-graph`
- Source sentence: SC/ST अभ्यर्थी जाति प्रमाण-पत्र अपलोड करें।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[
  {
    "attribute": "category",
    "operator": "IN",
    "value": [
      "SC",
      "ST"
    ],
    "unit": null,
    "reference_date": null
  }
]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [
    {
      "id": "upload_caste",
      "type": "upload_document",
      "optional": false
    }
  ],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 1,
  "unresolved": []
}
```

## hi-09

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `action-graph`
- Source sentence: पहले पंजीकरण करें, फिर दस्तावेज अपलोड करके आवेदन जमा करें।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [
    {
      "id": "register",
      "type": "register",
      "optional": false
    },
    {
      "id": "upload",
      "type": "upload_document",
      "optional": false
    },
    {
      "id": "submit",
      "type": "submit_application",
      "optional": false
    }
  ],
  "edges": [
    [
      "register",
      "upload"
    ],
    [
      "upload",
      "submit"
    ]
  ]
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 3,
  "unresolved": []
}
```

## hi-10

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `hi`
- Expected semantic type: `action-graph`
- Source sentence: अभ्यर्थी अपने रिकॉर्ड के लिए प्रति डाउनलोड कर सकते हैं।
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [
    {
      "id": "download",
      "type": "download",
      "optional": true
    }
  ],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 1,
  "unresolved": []
}
```

## te-01

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: అభ్యర్థి వయస్సు గరిష్టంగా 30 ఏళ్లు ఉండాలి.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "age",
    "operator": "<=",
    "value": 30,
    "unit": "years",
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## te-02

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: కనీసం 75 శాతం మార్కులు తప్పనిసరి.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "marks_percentage",
    "operator": ">=",
    "value": 75,
    "unit": null,
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## te-03

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: కుటుంబ వార్షిక ఆదాయం ₹2.5 లక్ష కంటే తక్కువ ఉండాలి.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "annual_family_income_inr",
    "operator": "<",
    "value": 250000,
    "unit": null,
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## te-04

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: B.Tech లేదా B.E. డిగ్రీ కలిగి ఉండాలి.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "education_level",
    "operator": "==",
    "value": "B.Tech",
    "unit": null,
    "reference_date": null
  },
  {
    "attribute": "education_level",
    "operator": "==",
    "value": "B.E.",
    "unit": null,
    "reference_date": null
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[
  {
    "operator": "OR",
    "members": [
      0,
      1
    ],
    "kind": null,
    "attribute": null,
    "delta": null,
    "target": null,
    "unresolved_without_base": null,
    "must_not_be_mandatory": null
  }
]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## te-05

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: 01.07.2026 నాటికి వయస్సు 30 ఏళ్లు మించకూడదు.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[
  {
    "attribute": "age",
    "operator": "<=",
    "value": 30,
    "unit": null,
    "reference_date": "2026-07-01"
  }
]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": true,
  "actions": 0,
  "unresolved": []
}
```

## te-06

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `eligibility/semantic-rule + applicability-guard`
- Source sentence: SC/ST అభ్యర్థులకు గరిష్ట వయస్సులో 5 సంవత్సరాల సడలింపు.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required. Relaxation/exemption/preference metadata is intentionally preserved as an unresolved adapter diagnostic.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[
  {
    "attribute": "category",
    "operator": "IN",
    "value": [
      "SC",
      "ST"
    ],
    "unit": null,
    "reference_date": null
  }
]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[
  {
    "operator": null,
    "members": [],
    "kind": "delta_relaxation",
    "attribute": "age",
    "delta": 5.0,
    "target": null,
    "unresolved_without_base": true,
    "must_not_be_mandatory": null
  }
]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 0,
  "unresolved": [
    "te-06:delta_relaxation"
  ]
}
```

## te-07

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `action-graph`
- Source sentence: ఆదాయ ధృవీకరణ పత్రం మరియు కుల ధృవీకరణ పత్రం పొందండి; తరువాత పత్రాలను అప్‌లోడ్ చేయండి.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [
    {
      "id": "income",
      "type": "obtain_document",
      "optional": false
    },
    {
      "id": "caste",
      "type": "obtain_document",
      "optional": false
    },
    {
      "id": "upload",
      "type": "upload_document",
      "optional": false
    }
  ],
  "edges": [
    [
      "income",
      "upload"
    ],
    [
      "caste",
      "upload"
    ]
  ]
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 3,
  "unresolved": []
}
```

## te-08

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `action-graph`
- Source sentence: ఫీజు చెల్లించిన తరువాత మాత్రమే దరఖాస్తు సమర్పించాలి.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [
    {
      "id": "pay",
      "type": "pay_fee",
      "optional": false
    },
    {
      "id": "submit",
      "type": "submit_application",
      "optional": false
    }
  ],
  "edges": [
    [
      "pay",
      "submit"
    ]
  ]
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 2,
  "unresolved": []
}
```

## te-09

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `applicability-guard + action-graph`
- Source sentence: SC/ST అభ్యర్థులు కుల ధృవీకరణ పత్రాన్ని అప్‌లోడ్ చేయాలి.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[
  {
    "attribute": "category",
    "operator": "IN",
    "value": [
      "SC",
      "ST"
    ],
    "unit": null,
    "reference_date": null
  }
]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [
    {
      "id": "upload_caste",
      "type": "upload_document",
      "optional": false
    }
  ],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 1,
  "unresolved": []
}
```

## te-10

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Scope: `synthetic semantic case`
- Language: `te`
- Expected semantic type: `eligibility/semantic-rule`
- Source sentence: అనుభవం ఉన్న అభ్యర్థులకు ప్రాధాన్యత ఇవ్వబడుతుంది.
- Current verification state: `NEEDS_HUMAN_VERIFICATION`
- Schema validation: `PASS`
- Deterministic adapter validation: `PASS`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: The strict schema and deterministic adapter validate this coherent synthetic case. Explicit human verification is still required. Relaxation/exemption/preference metadata is intentionally preserved as an unresolved adapter diagnostic.
- Atomic conditions (attribute, operator, value, unit/reference date):
```json
[]
```
- Guards / document applicability:
```json
[]
```
- AND/OR and relaxation/exemption/preference structure:
```json
[
  {
    "operator": null,
    "members": [],
    "kind": "preference_only",
    "attribute": null,
    "delta": null,
    "target": null,
    "unresolved_without_base": null,
    "must_not_be_mandatory": true
  }
]
```
- Actions, dependency edges, and optionality:
```json
{
  "actions": [],
  "edges": []
}
```
- Adapter result:
```json
{
  "eligibility_present": false,
  "actions": 0,
  "unresolved": [
    "te-10:preference_only"
  ]
}
```

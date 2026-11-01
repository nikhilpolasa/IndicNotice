# QA Human Review

> These are 30 real-notice QA candidates from two source PDFs. AI suggestions are not human verification. The original PDF is authoritative.

Use the source path and page shown for every decision. `READY_TO_VERIFY` means only that automated consistency checks found no issue.

## hi-q01

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `en`
- Question: What is the application deadline?
- Current answerability: `ANSWERABLE`
- Candidate answer: 2025-10-15
- Structured source field: `dates.application_deadline`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `1, 3`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6"
]
```
- Acceptable evidence groups:
```json
[
  [
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6"
  ],
  [
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0"
  ]
]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6",
    "text": "ऑनलाइन आवेदन-पत्र भरने की अंतिम तिथि\n\n15 अक्तूबर 2025"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "text": "ऑनलाइन आवेदन की अंतिम तिथि 15 अक्तूबर 2025 है |"
  }
]
```

## hi-q02

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `hi`
- Question: आवेदन की अंतिम तिथि क्या है?
- Current answerability: `ANSWERABLE`
- Candidate answer: 2025-10-15
- Structured source field: `dates.application_deadline`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `1, 3`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6"
]
```
- Acceptable evidence groups:
```json
[
  [
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6"
  ],
  [
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0"
  ]
]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6",
    "text": "ऑनलाइन आवेदन-पत्र भरने की अंतिम तिथि\n\n15 अक्तूबर 2025"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "text": "ऑनलाइन आवेदन की अंतिम तिथि 15 अक्तूबर 2025 है |"
  }
]
```

## hi-q03

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `te`
- Question: దరఖాస్తు చివరి తేదీ ఏమిటి?
- Current answerability: `ANSWERABLE`
- Candidate answer: 2025-10-15
- Structured source field: `dates.application_deadline`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `1, 3`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6"
]
```
- Acceptable evidence groups:
```json
[
  [
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6"
  ],
  [
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0"
  ]
]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b6",
    "text": "ऑनलाइन आवेदन-पत्र भरने की अंतिम तिथि\n\n15 अक्तूबर 2025"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "text": "ऑनलाइन आवेदन की अंतिम तिथि 15 अक्तूबर 2025 है |"
  }
]
```

## hi-q04

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `en`
- Question: Is there an application fee?
- Current answerability: `ANSWERABLE`
- Candidate answer: No application fee; ₹0.
- Structured source field: `fees`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b25"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b25",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b25",
    "text": "•\nइस परीिा के शलए कोई शुल्क नहीं शलया जायेगा|"
  }
]
```

## hi-q05 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass. This is a designated high-attention item.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `hi`
- Question: कौन से दस्तावेज चाहिए?
- Current answerability: `ANSWERABLE`
- Candidate answer: Income certificate after selection; caste certificate for SC/ST students; and disability certificate for candidates with disabilities. Aadhaar details are used for date of birth, but an Aadhaar upload is not explicitly required.
- Structured source field: `required_documents`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `3`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b12",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b13",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b19",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b20",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b22",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b23",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b25",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b26"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b12",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b12",
    "text": "1. फॉमड भरिे समय जन्मततर्थ केवल बच्चे के आधार कार्ि के ररकॉर्ि अनुसार ही भरी जाए क्योंकक NSP पोटडल पर फॉमड भरिे"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b13",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b13",
    "text": "समय सभी वववरण आधार अनुसार ही भरे जािे हैं | परीिा उपरान्ि मेररट शलस्ट िैयार करिे समय समान अंक प्राप्ि"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b19",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b19",
    "text": "3. यदद ववद्यािी NMMSS परीिा की मेररट शलस्ट में आ जािा है िो उसे छात्रवृति िभी दी जाएगी जब वह अपने मािा"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b20",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b20",
    "text": "वपिा की कुि आय का प्रमाण-पत्र SDM/ िहसीलदार से सत्यावपि करा कर अपने जजले के जजला समन्वयक कायाडलय,"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b22",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b22",
    "text": "4. अनुसूथचि जाति/ जनजाति के छात्र अपनी जाति का प्रमाण-पत्र प्रिम श्रेंणी मजजस्रेट या अन्य सिम अथधकारी द्वारा"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b23",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b23",
    "text": "बनवा कर उसकी सत्यावपि प्रति आवेदन के साि स्कैन करके upload करें अन्यिा छात्र को सामान्य श्रेणी में ही रिा"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b25",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b25",
    "text": "5. ददवयांग परीिािी अपना अशक्ििा प्रमाण-पत्र (प्रतिशि सदहि) अपने जजले के CMO से बनवा कर आवेदन के साि स्कैन"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b26",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b26",
    "text": "करके upload करें अन्यिा छात्र को सामान्य श्रेणी में ही रिा जायेगा|"
  }
]
```

## hi-q06 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `te`
- Question: దరఖాస్తు లింక్ ఏమిటి?
- Current answerability: `ANSWERABLE`
- Candidate answer: The notice says the online application link will be available on https://www.scertharyana.gov.in and https://www.bseh.org.in.
- Structured source field: `links`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `3`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b2",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b3"
]
```
- Acceptable evidence groups:
```json
[
  [
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b2",
    "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b3"
  ]
]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b2",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b2",
    "text": "प्रािी द्वारा आवेदन पत्र ऑनलाइन ही भरा जायेगा जजसका शलंक पररषद् की वेबसाइट www.scertharyana.gov.inििा"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b3",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b3",
    "text": "हररयाणा ववद्यालय शशिा बोर्ड की वेबसाइट www.bseh.org.in पर उपलब्ध होगा| प्रवेश-पत्र/ रोल नंबर परीिा तिथि से"
  }
]
```

## hi-q07 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass. This is a designated high-attention item.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `en`
- Question: Am I eligible?
- Current answerability: `PARTIAL`
- Candidate answer: Eligibility cannot be determined from the supplied profile.
- Structured source field: `eligibility`
- Structured eligibility expectation: `UNKNOWN`
- Missing-information expectation: `current_class, current_school_type, previous_class, previous_school_type, attempt_count, state`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `1, 2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b3",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b20",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b23",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b26",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b27",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b28"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b3",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b3",
    "text": "(कक्षा आठवी में अध्ययनरत ववद्यार्थियों के लिए)"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b20",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b20",
    "text": "•\nछात्र हररयाणा राज्य के केवि सरकारी/ अनुदान प्राप्त ववद्याियों में पढ़ रहें हों|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
    "text": "•\nछात्रों ने सातवीं कक्षा केवि सरकारी/ अनुदान प्राप्त ववद्याियों से 55% अंकों से पास की हो|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
    "text": "•\nपरीिािी के मािा-वपिा की सभी स्त्रोिों से कुि वावषिक आय ₹ 3,50,000 से कम होनी चादहये|\n\nनोट"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b23",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b23",
    "text": "•\nववद्यािी इस परीिा में केवल एक बार बैठ सकिा/ सकिी है|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b26",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b26",
    "text": "•\nआठवीं किा का अनुिीणड ववद्यािी इस परीिा में नहीं बैठ सकिा/ सकिी|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b27",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b27",
    "text": "•\nकेंद्रीय ववद्यािय, जवाहर नवोदय ववद्यािय, KGBV, ककसी भी आवासीय ववद्यािय तथा तनजी (Private)"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b28",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b28",
    "text": "ववद्याियों में पढने वाले छात्र इस परीिा में नहीं बैठ सकिे|"
  }
]
```

## hi-q08 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass. This is a designated high-attention item.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `hi`
- Question: पात्रता जानने के लिए कौन सी जानकारी कम है?
- Current answerability: `PARTIAL`
- Candidate answer: Missing: annual_family_income_inr, current_class, current_school_type, previous_class, previous_school_type, attempt_count, and state.
- Structured source field: `eligibility`
- Structured eligibility expectation: `UNKNOWN`
- Missing-information expectation: `annual_family_income_inr, current_class, current_school_type, previous_class, previous_school_type, attempt_count, state`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `1, 2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b3",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b20",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b23",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b26",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b27",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b28"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b3",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b3",
    "text": "(कक्षा आठवी में अध्ययनरत ववद्यार्थियों के लिए)"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b20",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b20",
    "text": "•\nछात्र हररयाणा राज्य के केवि सरकारी/ अनुदान प्राप्त ववद्याियों में पढ़ रहें हों|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
    "text": "•\nछात्रों ने सातवीं कक्षा केवि सरकारी/ अनुदान प्राप्त ववद्याियों से 55% अंकों से पास की हो|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
    "text": "•\nपरीिािी के मािा-वपिा की सभी स्त्रोिों से कुि वावषिक आय ₹ 3,50,000 से कम होनी चादहये|\n\nनोट"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b23",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b23",
    "text": "•\nववद्यािी इस परीिा में केवल एक बार बैठ सकिा/ सकिी है|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b26",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b26",
    "text": "•\nआठवीं किा का अनुिीणड ववद्यािी इस परीिा में नहीं बैठ सकिा/ सकिी|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b27",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b27",
    "text": "•\nकेंद्रीय ववद्यािय, जवाहर नवोदय ववद्यािय, KGBV, ककसी भी आवासीय ववद्यािय तथा तनजी (Private)"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b28",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b28",
    "text": "ववद्याियों में पढने वाले छात्र इस परीिा में नहीं बैठ सकिे|"
  }
]
```

## hi-q09 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass. This is a designated high-attention item.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `te`
- Question: దరఖాస్తు చేయడానికి నేను ఏమి చేయాలి?
- Current answerability: `ANSWERABLE`
- Candidate answer: Complete and submit the application online through the SCERT Haryana or BSEH website before 15 October 2025.
- Structured source field: `actions`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `3`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b1",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b2",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b3"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b0",
    "text": "ऑनलाइन आवेदन की अंतिम तिथि 15 अक्तूबर 2025 है |"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b1",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b1",
    "text": "अंतिम तिथि ककसी भी जस्िति में नहीं बढाई जाएगी|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b2",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b2",
    "text": "प्रािी द्वारा आवेदन पत्र ऑनलाइन ही भरा जायेगा जजसका शलंक पररषद् की वेबसाइट www.scertharyana.gov.inििा"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b3",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b3",
    "text": "हररयाणा ववद्यालय शशिा बोर्ड की वेबसाइट www.bseh.org.in पर उपलब्ध होगा| प्रवेश-पत्र/ रोल नंबर परीिा तिथि से"
  }
]
```

## hi-q10

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `en`
- Question: What annual family income limit is stated?
- Current answerability: `ANSWERABLE`
- Candidate answer: Below ₹3,50,000.
- Structured source field: `eligibility`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b22",
    "text": "•\nपरीिािी के मािा-वपिा की सभी स्त्रोिों से कुि वावषिक आय ₹ 3,50,000 से कम होनी चादहये|\n\nनोट"
  }
]
```

## hi-q11

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `en`
- Question: What is the interview venue?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## hi-q12

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `hi`
- Question: ड्रेस कोड क्या है?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## hi-q13 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass. This is a designated high-attention item.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `te`
- Question: పరీక్ష ఎప్పుడు మరియు ఎక్కడ జరుగుతుంది?
- Current answerability: `ANSWERABLE`
- Candidate answer: 30 November 2025, 11:00 AM to 2:00 PM, at examination centres across Haryana.
- Structured source field: `dates.exam_date`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `1, 3`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b8",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b9",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b9",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b10"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b8",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b8",
    "text": "हररयाणा ववद्यालय शशिा बोर्ड, शभवानी द्वारा 30 नवम्बर, 2025 को राज्य के ववशभन्न केन्रों पर उपरोक्ि परीिा का"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b9",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b9",
    "text": "आयोजन ककया जायेगा|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b9",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b9",
    "text": "परीिा की तिथि\n\nसमय"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b10",
    "exists": true,
    "page": 3,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p3:b10",
    "text": "30-11-2025\n\nप्रात: 11:00 बजे से बाद दोपहर 02:00 बजे तक"
  }
]
```

## hi-q14

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `en`
- Question: Who is the interview chairperson?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## hi-q15 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `AMBIGUOUS`
- AI rationale: QUESTION_AMBIGUITY: ‘minimum marks’ has multiple valid interpretations, so this item is recommended for exclusion from final scored gold.
- Notice/document ID: `b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2`
- Notice language / question language: `hi` / `hi`
- Question: न्यूनतम अंक कितने होने चाहिए?
- Current answerability: `PARTIAL`
- Candidate answer: The question is ambiguous: 55% concerns prior Class VII marks, while the exam has separate MAT/SAT qualifying marks (36, relaxed to 29 for listed categories).
- Structured source field: `eligibility`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf`
- Source page(s): `1, 2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b25",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b26",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b27",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b28",
  "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b25",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b25",
    "text": "परीिा\n\nसमय\nअथधकिम अंक\nअहडिा अंक"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b26",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b26",
    "text": "मानशसक योग्यिा परीिण (MAT)\n\n90 शमनट\n\n90\n\n36"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b27",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b27",
    "text": "बौद्थधक योग्यिा परीिण (SAT)\n\n90 शमनट\n\n90\n\n36"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b28",
    "exists": true,
    "page": 1,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p1:b28",
    "text": "नोट: अनुसूथचि जाति, वपछड़ी जाति एवं ददवयांग ववद्याथिडयों के शलए प्रत्येक भाग के अहडिा अंक 29 है|"
  },
  {
    "evidence_id": "ev:b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
    "exists": true,
    "page": 2,
    "block": "b3fb1ae40c39cb5fdcb1a85d5c1cc324bf1d189017144bdd8c46501a78379be2:p2:b21",
    "text": "•\nछात्रों ने सातवीं कक्षा केवि सरकारी/ अनुदान प्राप्त ववद्याियों से 55% अंकों से पास की हो|"
  }
]
```

### Required final-gold disposition for hi-q15

- **EXCLUDE FROM FINAL SCORED GOLD:** the current wording has multiple valid interpretations (Class-VII eligibility marks versus MAT/SAT qualifying marks).

Do not rewrite this item into an easier scored question and do not select it in the NLP-6 gold manifest.

## te-q01

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `en`
- Question: What is the application deadline?
- Current answerability: `ANSWERABLE`
- Candidate answer: 2025-03-21
- Structured source field: `dates.application_deadline`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `1`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "text": "• Last Date for Submission of Online Applications: 21st March 2025"
  }
]
```

## te-q02

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `hi`
- Question: आवेदन की अंतिम तिथि क्या है?
- Current answerability: `ANSWERABLE`
- Candidate answer: 2025-03-21
- Structured source field: `dates.application_deadline`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `1`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "text": "• Last Date for Submission of Online Applications: 21st March 2025"
  }
]
```

## te-q03

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `te`
- Question: దరఖాస్తు చివరి తేదీ ఏమిటి?
- Current answerability: `ANSWERABLE`
- Candidate answer: 2025-03-21
- Structured source field: `dates.application_deadline`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `1`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "text": "• Last Date for Submission of Online Applications: 21st March 2025"
  }
]
```

## te-q04

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `en`
- Question: When does application registration open?
- Current answerability: `ANSWERABLE`
- Candidate answer: 2025-03-07
- Structured source field: `dates.application_open`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `1`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b3"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b3",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b3",
    "text": "This is to inform all the parents and guardians that the online admission\nprocess for Class I& Balvatika-III in Kendriya Vidyalayas for the\nacademic year 2025- 2026 will commence from 7th March 2025.\nThe details are as follows:"
  }
]
```

## te-q05 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `hi`
- Question: आवेदन का लिंक क्या है?
- Current answerability: `ANSWERABLE`
- Candidate answer: Class I: https://kvsonlineadmission.kvs.gov.in; Balvatika-III: https://balvatika.kvs.gov.in/
- Structured source field: `links`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "exists": true,
    "page": 2,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "text": "categories 1 to 4 listed above\nNote: Preference in Admission to wards will be based on the number of\ntransfers of the parents in the last 7 years\nFor online Registration follow the link:\nClass-1:https://kvsonlineadmission.kvs.gov.in\nBalvatika-III: https://balvatika.kvs.gov.in/\nFor Further Admission Guidelines and admission Notice please\nscan the QR code below:"
  }
]
```

## te-q06

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `te`
- Question: దరఖాస్తు ఎలా చేయాలి?
- Current answerability: `ANSWERABLE`
- Candidate answer: Register online and submit before the deadline.
- Structured source field: `actions`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `1, 2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b7",
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b7",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b7",
    "text": "• We advise all interested candidates to submit their applications before\nthe last date to ensure timely processing. Please apply in your\ncategory only. Kindly visit the official KVS website for further\ndetails regarding the eligibility criteria, required documents, and the\nadmission procedure."
  },
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "exists": true,
    "page": 2,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "text": "categories 1 to 4 listed above\nNote: Preference in Admission to wards will be based on the number of\ntransfers of the parents in the last 7 years\nFor online Registration follow the link:\nClass-1:https://kvsonlineadmission.kvs.gov.in\nBalvatika-III: https://balvatika.kvs.gov.in/\nFor Further Admission Guidelines and admission Notice please\nscan the QR code below:"
  }
]
```

## te-q07 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass. This is a designated high-attention item.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `en`
- Question: What documents are required?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## te-q08

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `hi`
- Question: प्रवेश वरीयता किस आधार पर है?
- Current answerability: `ANSWERABLE`
- Candidate answer: Number of parent transfers in the last 7 years.
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "exists": true,
    "page": 2,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "text": "categories 1 to 4 listed above\nNote: Preference in Admission to wards will be based on the number of\ntransfers of the parents in the last 7 years\nFor online Registration follow the link:\nClass-1:https://kvsonlineadmission.kvs.gov.in\nBalvatika-III: https://balvatika.kvs.gov.in/\nFor Further Admission Guidelines and admission Notice please\nscan the QR code below:"
  }
]
```

## te-q09

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `te`
- Question: ఫీజు ఎంత?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `fees`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## te-q10

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `en`
- Question: Where is the examination venue?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## te-q11

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `hi`
- Question: ड्रेस कोड क्या है?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## te-q12

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `te`
- Question: నేను అర్హుడినా?
- Current answerability: `UNANSWERABLE`
- Candidate answer: `NOT_STATED`
- Structured source field: `NONE`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `NONE`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[]
```

## te-q13 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `en`
- Question: What is the notice title?
- Current answerability: `ANSWERABLE`
- Candidate answer: Kendriya Vidyalaya Sangathan (KVS) Admission Schedule for Class I & Balvatika-III – 2025-2026
- Structured source field: `metadata.title`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `1`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b1",
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b2"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b1",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b1",
    "text": "Kendriya Vidyalaya Sangathan (KVS) Admission Schedule for"
  },
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b2",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b2",
    "text": "Class I & Balvatika-III – 2025-2026"
  }
]
```

## te-q14 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation references resolve and current semantic-support checks pass. This is a designated high-attention item.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `hi`
- Question: आवेदन कब और कहाँ जमा करना है?
- Current answerability: `ANSWERABLE`
- Candidate answer: Submit online only by 21 March 2025. Use https://kvsonlineadmission.kvs.gov.in for Class I or https://balvatika.kvs.gov.in/ for Balvatika-III, as applicable.
- Structured source field: `dates.application_deadline, actions.channel, links`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `1, 2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `1.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b6",
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b5",
    "text": "• Last Date for Submission of Online Applications: 21st March 2025"
  },
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b6",
    "exists": true,
    "page": 1,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p1:b6",
    "text": "• Mode of Application: Online only (Please visit the official KVS\nadmission portal)"
  },
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "exists": true,
    "page": 2,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "text": "categories 1 to 4 listed above\nNote: Preference in Admission to wards will be based on the number of\ntransfers of the parents in the last 7 years\nFor online Registration follow the link:\nClass-1:https://kvsonlineadmission.kvs.gov.in\nBalvatika-III: https://balvatika.kvs.gov.in/\nFor Further Admission Guidelines and admission Notice please\nscan the QR code below:"
  }
]
```

## te-q15 — high-attention

- Human decision: **[ ] VERIFY  [ ] CORRECT  [ ] EXCLUDE  [ ] LEAVE UNVERIFIED**
- Verification state: `NEEDS_HUMAN_VERIFICATION`
- AI audit suggestion: `READY_TO_VERIFY`
- AI rationale: Citation IDs resolve. The lexical/normalization-sensitive support heuristic returned 0.0, which is review assistance only and is not evidence that the annotation is incorrect; a human must verify the claim-to-evidence relation.
- Notice/document ID: `06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc`
- Notice language / question language: `mixed` / `te`
- Question: ఆన్‌లైన్ నమోదు లింక్ ఏది?
- Current answerability: `ANSWERABLE`
- Candidate answer: Class I: https://kvsonlineadmission.kvs.gov.in; Balvatika-III: https://balvatika.kvs.gov.in/
- Structured source field: `links`
- Structured eligibility expectation: `NONE`
- Missing-information expectation: `NONE`
- Source PDF: `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf`
- Source page(s): `2`
- Citation IDs exist: `True`
- Citation semantic support under current evaluator: `0.0`
- Expected citation IDs:
```json
[
  "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12"
]
```
- Acceptable evidence groups:
```json
[]
```
- Source evidence:
```json
[
  {
    "evidence_id": "ev:06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "exists": true,
    "page": 2,
    "block": "06a874c63f00198da8aa75b1380029cdd683f0e36e3055d28fad8c4fc0352ffc:p2:b12",
    "text": "categories 1 to 4 listed above\nNote: Preference in Admission to wards will be based on the number of\ntransfers of the parents in the last 7 years\nFor online Registration follow the link:\nClass-1:https://kvsonlineadmission.kvs.gov.in\nBalvatika-III: https://balvatika.kvs.gov.in/\nFor Further Admission Guidelines and admission Notice please\nscan the QR code below:"
  }
]
```

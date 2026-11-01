# IndicNotice — Model / Backend Registry

## Status vocabulary
- **PLANNED** — candidate only
- **AVAILABLE_NOT_TESTED** — available but no verified real inference
- **TESTED** — real inference executed successfully
- **BLOCKED** — technical/access blocker
- **GATED** — model access gated
- **INCOMPATIBLE** — dependency/runtime incompatibility
- **NOT_SELECTED** — intentionally not chosen for current milestone

Never mark a backend **TESTED** unless actual inference ran in the active repository/environment.

## Native PDF
| Function | Candidate | Role | Status |
|---|---|---|---|
| Native PDF extraction | PyMuPDF 1.28.2 | Primary digital-PDF text/layout extraction | TESTED |

## OCR
| Function | Candidate | Role | Status |
|---|---|---|---|
| Baseline OCR | Tesseract 5.5.3 + `tessdata_fast` (`tel`, `hin`, `eng`) | Academic baseline / first OCR adapter | TESTED |
| Strong Indic OCR | IIIT-H IndicOCR | Preferred stronger candidate if feasible | GATED |
| Alternative OCR | PaddleOCR | Fallback/experimental backend | NOT_SELECTED |
| Alternative Indic OCR | Anuvaad OCR | Optional baseline/reference | NOT_SELECTED |

Policy: make one reliable OCR backend work first; do not destabilize the environment to install every candidate.

Tesseract actual inference ran on all 10 image-only pages of `ananthapuramu_anganwadi_recruitment_2025.pdf`; TSV geometry and confidence were mapped to canonical evidence. IIIT-H's public IndicOCR material describes a 22-language demo, but no reproducible local weights/install/API contract or repository license was found, so it is not represented as integrated. PaddleOCR's official documentation lists Telugu and Devanagari recognition models and Python 3.12-compatible installation; it was deliberately not installed after the required reliable baseline passed.

## Layout/document resources
| Resource | Intended use | Status |
|---|---|---|
| IndicDLP | Indic layout/document research resource | PLANNED |
| LayoutLMv3 | Literature/baseline reference | PLANNED |
| LayoutXLM | Multilingual layout-aware reference | PLANNED |
| Donut | OCR-free document-understanding reference | PLANNED |
| Patram-Bench | Indic document-understanding benchmark/reference | PLANNED |
| DocILE | KIE/evaluation methodology reference | PLANNED |
| ExtractBench | Schema-guided extraction methodology reference | PLANNED |

## Language identification
| Candidate | Role | Status |
|---|---|---|
| Unicode-range detector | CPU-safe Telugu/Devanagari/Latin/MIXED baseline | TESTED |
| IndicLID | Optional learned language-ID backend | NOT_SELECTED |

Caveat: Devanagari is not uniquely Hindi; script detection is only a baseline.

## Structured extraction
| Candidate | Role | Status |
|---|---|---|
| Regex/keyword rules (`regex-baseline-nlp2-v1`) | NLP-2 interpretable baseline | TESTED |
| Qwen3-4B GGUF, `Q4_K_M` | NLP-3 contextual structured extraction | TESTED |
| IndicBERT-v3 (270M if fine-tuning justified) | Optional encoder experiment | PLANNED |
| IndicNER | Auxiliary generic NER, not full eligibility parser | PLANNED |

## Retrieval
| Candidate | Role | Status |
|---|---|---|
| Unicode BM25 (`unicode-bm25-nlp5-v1`) | Interpretable in-memory evidence retrieval baseline | TESTED |
| BGE-M3 | Multilingual retrieval for longer documents | NOT_SELECTED |
| multilingual E5 | Simpler multilingual retrieval alternative | NOT_SELECTED |

## Translation
| Candidate | Role | Status |
|---|---|---|
| IndicTrans2 | Telugu ↔ Hindi translation with fact-preservation checks | PLANNED |

## QA
| Candidate/resource | Role | Status |
|---|---|---|
| Schema-first grounded QA (`schema-first-grounded-qa-nlp5-v1`) | Primary structured/retrieval QA service | TESTED |
| IndicQA | Benchmark/methodology/reference | PLANNED |

## Optional multimodal baseline
| Candidate | Role | Status |
|---|---|---|
| Qwen3-VL-family model | Direct page/image → structured JSON comparison | PLANNED |

## Speech stretch
| Candidate | Role | Status |
|---|---|---|
| IndicConformer | Hindi/Telugu ASR | PLANNED |

## Environment notes
NLP-1 was tested in repository-local Python 3.12.10 on Windows 11. The host default Python 3.13.7 was not modified. Tesseract and language data are repository-local ignored tools; setup instructions and exact versions are recorded in the milestone report. NVIDIA RTX 4050 hardware was present, but the tested pipeline is CPU-only and did not require CUDA.

`regex-baseline-nlp2-v1` is dependency-free beyond the frozen project runtime.
It completed synthetic/adversarial unit coverage and real inference on the native
Hindi NMMSS fixture. The six searchable official fixtures form only a smoke
evaluation slice; the registry does not claim corpus-level quality or calibrated
confidence.

### NLP-3 tested contextual backend

`Qwen/Qwen3-4B-GGUF` was tested at repository revision
`bc640142c66e1fdd12af0bd68f40445458f3869b`, file
`Qwen3-4B-Q4_K_M.gguf`, SHA-256
`7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.
The checkpoint is Apache-2.0 licensed. It ran locally through llama.cpp release
`b11429` / commit `d81235049384534c167caea52b85a694f6103d14` using the Vulkan
Windows x64 build (release archive SHA-256
`1bfe78ad9168b79fa02bf67f6af9f5e17a966d824d77238517f7bef12ac73b36`).

Real schema-valid inference completed on the Hindi SCERT Haryana NMMSS notice
and Telugu/English KVS Kadapa admission notice on an NVIDIA GeForce RTX 4050
Laptop GPU (6,141 MiB, driver 581.86). The tested runtime used 16,384 context
tokens, all GPU layers, reasoning off, 4,096 output tokens, temperature 0.2,
top-p 0.8, presence penalty 1.5, and seed 42. `indicnotice-contextual-v1`
prompts and 3,000-character evidence chunks were used.

Known limitations are material: on the two-document verified-complete smoke
slice, this quantized model underperformed NLP-2, needed a repair for every
chunk, generated many claims rejected by deterministic grounding, and required
about 11.7 minutes for Hindi and 4.3 minutes for Telugu. TESTED means the real
backend executed successfully; it does not mean quality is production-ready.

### NLP-5 retrieval and QA status

`unicode-bm25-nlp5-v1` and the schema-first QA service ran on the recorded real
Hindi and Telugu analyses. The eight-case smoke output includes actual lexical
scores, citations and abstentions. The optional grounded-generator adapter was
validated with deterministic fake-provider unit tests, including malformed
output and provider failure, but no real generative QA inference ran. No QA
generator backend is therefore added to the registry. Qwen's separate NLP-3
structured-extraction status remains `TESTED` and is not extrapolated to QA.

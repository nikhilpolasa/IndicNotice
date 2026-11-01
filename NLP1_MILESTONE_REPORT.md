# IndicNotice NLP-1 Milestone Report

## 1. Final status

PASSED

## 2. Executive summary

NLP-1 now ingests validated PDF, PNG, JPEG/JPG input and maps both native PDF text and real OCR output into the frozen `Document`, `DocumentPage`, `DocumentBlock`, and `EvidenceSpan` contracts. PyMuPDF performs native extraction; deterministic page-level routing sends deficient pages to a real Tesseract backend with Telugu, Hindi, and English data. The implementation retains SHA-256 identity, page/block provenance, geometry, reading order, page-relative character offsets, raw OCR text, and reported confidence.

A genuine 20-page Hindi government recruitment PDF completed native extraction. A genuine 10-page image-only Telugu government recruitment notice completed full Tesseract inference. The schema 1.0 contracts were not modified, and no NLP-2 functionality was added.

## 3. Environment

- OS: Windows 11, build `10.0.26300`
- Host Python: 3.13.7 (left unchanged)
- NLP-1 environment: repository-local `.venv`, Python 3.12.10
- GPU: NVIDIA GeForce RTX 4050 Laptop GPU, 6,141 MiB; driver 581.86; reported CUDA 13.0
- Tested path: CPU-only; no CUDA dependency
- PyMuPDF 1.28.2; Pillow 12.3.0; Pydantic 2.14.1; pytest 9.1.1
- Tesseract 5.5.3.20260724, repository-local extracted distribution
- Tesseract languages verified by the binary: `eng`, `hin`, `tel`
- Disk observed before downloads: approximately 19.7 GiB free on C:

The Python 3.12 venv was chosen because it is a stable compatibility target for PDF/OCR dependencies and avoids forcing packages into the existing Python 3.13 installation.

## 4. Repository baseline

- All authoritative files named in the request existed and were read before implementation.
- `docs/NLP_MASTER_PLAN.md` exists; this conflicts with the historical statement in `NLP0_FINAL_AUDIT.md` that an earlier audit could not find it. The current workspace is the source of truth.
- The workspace initially had no `.git`; `git init` created a local repository only. No remote or history was manufactured.
- Pre-change command: `python -m pytest -p no:cacheprovider -q`
- Result: **187 passed, 0 failed in 0.69 s**.
- Frozen contract version: schema 1.0.
- `NLP0_FINAL_AUDIT.md` says it was reconstructed from a chat summary. Its claims were therefore treated as context and independently verified where relevant.

## 5. Architecture implemented

```text
PDF / PNG / JPEG
  -> boundary validation + SHA-256
  -> PDF: page-level native quality decision
       -> usable: PyMuPDF blocks
       -> deficient: rendered page -> OCRBackend
     image: OCRBackend
  -> conservative normalization
  -> block/document script identification
  -> canonical Document/Page/Block + EvidenceSpan collection
```

`IngestionResult` is a service wrapper around the frozen canonical objects, not a parallel document schema.

## 6. Files created/modified

Created:

- `services/nlp/ingestion/{__init__,errors,native_pdf,normalization,router,types,validation}.py`
- `services/nlp/ocr/{__init__,tesseract}.py`
- `services/nlp/language_id/{__init__,script_detector}.py`
- `services/nlp/evaluation/{__init__,ocr_metrics}.py`
- `tests/unit/test_nlp1_ingestion.py`
- `tests/unit/test_nlp1_text_utilities.py`
- `tests/integration/test_nlp1_real_documents.py`
- `datasets/fixtures/nlp1/PROVENANCE.md`
- two public PDF fixtures and one manually verified title transcription
- `.gitignore`
- this report

Modified:

- `pyproject.toml`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/MODEL_REGISTRY.md`
- `docs/EVALUATION_PLAN.md`

The only pre-existing infrastructure correction was changing the invalid setuptools backend `setuptools.backends.legacy:build` to `setuptools.build_meta:__legacy__`, which was necessary for editable installation.

## 7. Ingestion layer

The boundary verifies existence, regular-file status, nonzero size, configurable maximum bytes, supported extension, PDF/PNG/JPEG signature, extension/signature agreement, and image decodability. PDFs additionally receive corruption, encryption, zero-page, and configurable page-limit checks. Failures use specific `IngestionError` subclasses and do not become empty successful documents.

Document content is never interpreted as a command. Tesseract is called with a fixed argument list and `shell=False`; extracted URLs, PDF actions, or strings are not executed.

## 8. Native PDF extraction

PyMuPDF maps native text blocks into canonical blocks and evidence spans with stable hash-derived identifiers, 1-indexed pages, dimensions, bounding boxes, deterministic reading order, and page-relative offsets. Pages remain distinct. The 20-page Hindi fixture produced 43,183 normalized characters and 390 evidence spans.

## 9. Native/OCR routing

The default quality threshold is 20 letters/digits per page. Pages meeting it stay native; deficient pages alone are rendered at configurable DPI and passed to the configured OCR adapter. Unit tests cover a mixed two-page PDF with one native and one OCR page. All ten pages in the Telugu fixture had zero native alphanumeric characters and were routed to OCR.

## 10. OCR backends

| Backend | Status | Languages | Actual inference executed? | Fixture | Notes |
|---|---|---|---|---|---|
| Tesseract 5.5.3 | TESTED | `tel+hin+eng` | Yes, all 10 pages | Telugu Anganwadi notice | TSV parsed into line blocks, bbox and mean word confidence retained |
| IIIT-H IndicOCR | GATED | Claims 22 Indian languages | No | None | Public demo/paper found; no reproducible local weights/install/API contract or suitable repository license found |
| PaddleOCR | NOT_SELECTED | Official Telugu and Devanagari models available | No | None | Python 3.12 path appears feasible, but a second large stack was optional and would not improve the acceptance gate by itself |
| IndicPhotoOCR | AVAILABLE_NOT_TESTED | Hindi, Telugu and other Indic languages | No | None | Candidate for later controlled comparison, not NLP-1 scope |

Tesseract is installed locally by extracting the approved Chocolatey package because the vendor installer requested Windows elevation. Official `tessdata_fast` files were downloaded from the Tesseract organization. `.tools/` is intentionally ignored.

## 11. Language/script identification

`ScriptHeuristicDetector` counts Unicode letters in Telugu, Devanagari, and Latin ranges; digits/punctuation are ignored. It returns `te`, `hi`, `en`, `mixed`, or `unknown` using proportions and minimum-letter thresholds. Labels are applied per block and document. `hi` means “Devanagari under this project baseline,” not guaranteed semantic Hindi. The scanned Telugu OCR is honestly labeled `mixed` because recognition noise and genuine English identifiers produced material Latin-script content.

IndicLID is MIT-licensed and downloadable, but its fastText/model dependency was not needed for the required baseline and is recorded as NOT_SELECTED.

## 12. Evidence preservation

- Native and OCR outputs use the same frozen canonical schemas.
- Every span references its SHA-256 document ID and page.
- Bounding boxes and deterministic block IDs are preserved.
- OCR `original_ocr_text` and reported confidence are retained; no confidence is invented.
- Character offsets index normalized page text.
- Table IDs/rows/columns/headers remain null because the baselines do not derive them reliably.
- Native `original_ocr_text` remains null as required by the frozen contract.
- JSON serialization round-trip is tested.

## 13. Real fixtures

| Fixture | Language | Category | Issuer/source | Digital/scanned | Provenance | Processing route |
|---|---|---|---|---|---|---|
| `nfc_recruitment_01_2026_hindi.pdf` | Hindi + identifiers | Recruitment | Nuclear Fuel Complex, Department of Atomic Energy, Government of India | Digital, 20 pages | NFC public website; SHA-256 in `PROVENANCE.md` | Native PyMuPDF on 20/20 pages |
| `ananthapuramu_anganwadi_recruitment_2025.pdf` | Telugu + identifiers | Recruitment | Women Development & Child Welfare Department, Ananthapuramu District, Andhra Pradesh | Scanned, 10 pages | AP district public website/S3WaaS; SHA-256 in `PROVENANCE.md` | Tesseract on 10/10 pages |

Both were retrieved on 2026-10-12. No blanket redistribution license was identified; the issuer URLs and inclusion caveat are retained beside the fixtures.

## 14. Example real extraction

Native Hindi excerpt:

```text
भारत सरकार
परमाणु उजाᭅ िवभाग
...
िव᭄ापन ... NFC/01/2026
```

Real Telugu OCR excerpt (kept verbatim, including an OCR error):

```text
ఆంధప్రదేశ్ ప్రభుత్వం
```

Manually verified source title:

```text
ఆంధ్రప్రదేశ్ ప్రభుత్వం
```

## 15. OCR metrics tooling

`character_error_rate()` uses Unicode code points and `word_error_rate()` uses whitespace tokens. Both use exact Levenshtein edit distance. Empty-reference behavior is explicit and tested. Rates are not clamped, because insertion-heavy hypotheses can legitimately exceed 1 for non-empty references.

## 16. CER/WER smoke-test results

For the two-word, manually transcribed Telugu page-1 title:

- Reference: `ఆంధ్రప్రదేశ్ ప్రభుత్వం`
- Tesseract prediction: `ఆంధప్రదేశ్ ప్రభుత్వం`
- CER: **0.090909**
- WER: **0.5**

This tiny sample verifies the end-to-end measurement path only. It is not a representative benchmark or evidence of broad OCR quality.

## 17. Tests added

Twenty fast unit test cases cover signatures and hashing; PDF/PNG/JPEG paths; empty, corrupt, encrypted, mismatched, and unsupported input; page limits; native page/block/evidence mapping; mixed routing; Telugu/Devanagari/Latin/mixed/unknown script behavior; conservative normalization; typed Tesseract failures; zero-confidence preservation; evidence JSON round-trip; and CER/WER correctness.

Two marked integration tests cover the real Hindi native PDF and full real Telugu Tesseract OCR.

## 18. Commands actually executed

Key reproducible commands included:

```powershell
python -m pytest -p no:cacheprovider -q
py -3.12 -m venv .venv
python -m pip --python .\.venv\Scripts\python.exe install -e ".[dev,nlp1]"
.\.venv\Scripts\python.exe -m compileall -q services\nlp indicnotice
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\unit -q
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\integration -q --durations=10
```

The real fixture URLs are recorded in provenance, and the exact Tesseract/model retrieval URLs are listed below. Downloaded installers/caches and extracted tools are ignored rather than committed.

Repository-local OCR setup used these reproducible sources:

```text
https://community.chocolatey.org/api/v2/package/tesseract/5.5.3.20260724
https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata
https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/hin.traineddata
https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/tel.traineddata
```

The Chocolatey `.nupkg` and its NSIS payload were extracted with 7-Zip into `.tools/Tesseract-OCR`; no elevated/system install was performed.

## 19. Final test results

- Pre-change frozen baseline: **187 passed, 0 failed**.
- Unit suite after NLP-1: **207 passed, 0 failed in 0.84 s**.
- Integration suite: **2 passed, 0 failed in 38.19 s**.
- Real native backend inference: executed successfully.
- Real Tesseract backend inference: executed successfully on all ten scan pages.
- Coverage verification: **209 passed, 0 failed in 48.02 s**; total coverage **90%**.
- Final end-state combined suite after the conservative joiner-preservation review: **209 passed, 0 failed in 46.66 s**.

## 20. Performance observations

- Hindi digital notice: 20 pages, native route, **0.14 s** in the integration test.
- Telugu scanned notice: 10 pages, 250 DPI render + CPU Tesseract, **37.81 s** in the integration test (about 3.8 s/page).
- Telugu output: 14,082 characters, 387 evidence spans; page mean confidences ranged approximately 0.628–0.873 in the manual smoke run.
- No GPU was required. Memory was not profiled, but no obvious pressure or failure occurred.
- The 50 MiB input and 250-page defaults are configurable safety limits, not benchmark-derived product limits.

## 21. Failed/blocked integrations

- The first direct UB Mannheim installer URL returned HTTP 403. Chocolatey's approved Tesseract package was downloaded, and its contained installer was extracted locally without elevation.
- Silent installer execution was cancelled by Windows elevation; no system install was made.
- IIIT-H IndicOCR: GATED as described above; no fake adapter or TESTED claim was created.
- PaddleOCR: NOT_SELECTED, not failed. Its official support looks viable, but it was optional and unnecessary for a stable NLP-1 pass.
- IndicLID: NOT_SELECTED, not failed. The deterministic script detector satisfies this milestone.

## 22. Known limitations

- The native usability heuristic is intentionally simple and may miss pages with enough garbage characters or very small useful text over an image.
- PyMuPDF native output reflects the PDF's encoding quality; the Hindi fixture includes some unusual source glyph mappings.
- Tesseract quality on the scanned Telugu fixture is visibly imperfect and frequently introduces Latin noise.
- `mixed` is script mixture, not semantic language identification.
- The frozen `DocumentPage` has no page-language field; labels exist at block and document level.
- No table structure, handwriting specialization, OCR correction, or semantic extraction is attempted.
- Rendered page images are development cache artifacts; there is no persistent OCR result cache.

## 23. Contract-change requests

NONE

The frozen schema represented the required provenance when canonical evidence spans were returned alongside the canonical document in `IngestionResult`.

## 24. NLP-1 acceptance-gate checklist

- [x] Authoritative documents read and repository state verified
- [x] 187-test baseline independently reproduced
- [x] Frozen NLP-0 regression suite preserved
- [x] Real Hindi public notice ingested
- [x] Real Telugu public notice ingested
- [x] Genuine scanned notice processed by genuine OCR
- [x] PyMuPDF native extraction executed
- [x] Tesseract executable and `tel`/`hin`/`eng` data verified
- [x] Native/OCR convergence into canonical contracts
- [x] Page/block provenance, bbox, confidence, and offsets retained
- [x] Script/language labels and mixed-script tests
- [x] CER and WER utilities tested
- [x] Fixture provenance documented without fabrication
- [x] Backend statuses reflect actual execution
- [x] No NLP-2 implementation

## 25. Recommended NLP-2 next step

Freeze this ingestion boundary and build an interpretable, evidence-linked regex/keyword extraction baseline over `IngestionResult.document` and its canonical spans. Start with a small annotated Telugu/Hindi development set and fields such as issuer, reference number, and typed dates; do not change NLP-1 evidence semantics to accommodate extractor convenience.

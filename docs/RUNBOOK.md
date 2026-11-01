# IndicNotice Reproducibility Runbook (NLP-1 through NLP-5)

Verified against repository commit `5c23145` on 2026-10-14. Commands use
Windows PowerShell and assume the repository-local Python environment unless a
command explicitly says otherwise.

## 1. Purpose of this runbook

This is the authoritative manual execution guide for the implemented
IndicNotice NLP core through NLP-5. It covers:

| Stage | Implemented role |
|---|---|
| NLP-0 | Frozen schema 1.0, validators, deterministic evaluator, and adapter foundation; normally tested rather than run as a standalone pipeline |
| NLP-1 | Validated document ingestion, native PDF extraction, OCR, script labels, and evidence preservation |
| NLP-2 | Independently runnable deterministic regex/rule extraction baseline |
| NLP-3 | Independently runnable contextual Qwen extraction experiment |
| NLP-4 | Separately runnable evidence-gated hybrid semantic method using deterministic extraction plus contextual candidates |
| NLP-5 | Schema-first grounded QA over canonical analysis and evidence |

NLP-2, NLP-3, and NLP-4 are experimental methods with distinct outputs. They
do not successively overwrite one another. NLP-4 may consume recorded NLP-3
candidates, but retains separate NLP-2/NLP-3/NLP-4 comparisons. NLP-5 consumes
the canonical NLP-4 analyses in the checked-in real smoke report.

NLP-6 has not started. This runbook does not define or execute final evaluation.

## 2. Project directory

The verified project root on the current Windows machine is:

```text
<repository-root>
```

Open PowerShell at any location inside the repository and resolve its root from Git:

```powershell
Set-Location -LiteralPath (git rev-parse --show-toplevel)
Get-Location
```

Expected location:

```text
<repository-root>
```

Run every command in this guide from that root unless explicitly stated.

## 3. Git / checkpoint status

Verified milestone commits are:

| Milestone | Commit | Subject |
|---|---|---|
| NLP-1 | `1619f50` | `Complete NLP-1 document ingestion and OCR pipeline` |
| NLP-2 | `4596ea5` | `Complete NLP-2 interpretable extraction baseline` |
| NLP-3 | `a9bb18f` | `Complete NLP-3 contextual extraction milestone` |
| NLP-4 | `65549b6` | `Complete NLP-4 evidence-gated semantic milestone` |
| NLP-5 | `5c23145` | `Complete NLP-5 grounded question answering` |

Inspect the current state without changing it:

```powershell
git status --short
git log --oneline --decorate -5
```

An empty `git status --short` result means the working tree has no tracked or
untracked changes. Do not reset or revert merely because the tree is dirty;
first identify whether the changes belong to another team member.

Known documentation discrepancy: `README.md` still labels NLP-3 through NLP-5
as pending and calls NLP-2 the current milestone. The later milestone commits,
scripts, reports, tests, and `docs/NLP_MASTER_PLAN.md` show NLP-1 through NLP-5
complete. This runbook follows the verified repository state and does not edit
the stale README during this documentation-only task.

## 4. Verified software environment

The normal repository runtime is **not** the host-default `python` command.

| Component | Verified current value | Kind |
|---|---|---|
| Operating system | Microsoft Windows `10.0.26300.9550` (milestone report identifies Windows 11) | OS |
| Host `python` | `C:\Python313\python.exe`, Python 3.13.7 | Host Python; not the tested NLP runtime |
| Repository Python | `.venv\Scripts\python.exe`, Python 3.12.10 | Python runtime |
| pytest | 9.1.1 | Python package |
| pytest-cov | 7.1.0 | Python package |
| Pydantic | 2.14.1 | Python package |
| PyMuPDF (`pymupdf`) | 1.28.2 | Python package |
| Pillow (`PIL`) | 12.3.0 | Python package |
| `pytesseract` | Not installed and not used | Not a dependency |
| Tesseract | 5.5.3.20260724 | External executable |
| OCR language data | `eng`, `hin`, `tel` | External Tesseract data |
| llama.cpp | build 11429, commit `d81235049`, Windows Vulkan build | External executable/runtime |
| Qwen checkpoint | `Qwen3-4B-Q4_K_M.gguf`, 2,497,280,256 bytes | External model file |

The OCR adapter invokes Tesseract directly with `subprocess`; it does not use
the `pytesseract` Python wrapper. External tools and models are under ignored
`.tools/`, so a fresh clone will not contain them.

Verified local paths:

```text
.tools\Tesseract-OCR\tesseract.exe
.tools\Tesseract-OCR\tessdata\eng.traineddata
.tools\Tesseract-OCR\tessdata\hin.traineddata
.tools\Tesseract-OCR\tessdata\tel.traineddata
.tools\llama.cpp-b11429\llama-server.exe
.tools\models\Qwen3-4B-Q4_K_M.gguf
```

Model SHA-256:
`7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.
The llama.cpp release archive SHA-256 is
`1bfe78ad9168b79fa02bf67f6af9f5e17a966d824d77238517f7bef12ac73b36`.

## 5. Environment health check

Use the repository interpreter for Python checks:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -m pytest --version
.\.venv\Scripts\python.exe -c "import pymupdf; print(pymupdf.__version__)"
.\.venv\Scripts\python.exe -c "import PIL; print(PIL.__version__)"
.\.venv\Scripts\python.exe -c "import pydantic; print(pydantic.__version__)"
```

Expected versions are Python 3.12.10, pytest 9.1.1, PyMuPDF 1.28.2, Pillow
12.3.0, and Pydantic 2.14.1. Confirm the external OCR installation separately:

```powershell
.\.tools\Tesseract-OCR\tesseract.exe --version
.\.tools\Tesseract-OCR\tesseract.exe --list-langs
```

The language list must contain `eng`, `hin`, and `tel`. Check the existing
llama.cpp binary and model identity without starting a server:

```powershell
.\.tools\llama.cpp-b11429\llama-server.exe --version
Get-FileHash .\.tools\models\Qwen3-4B-Q4_K_M.gguf -Algorithm SHA256
```

## 6. Dependency installation / restoration

The verified Python environment creation and editable install procedure comes
from `README.md` and `pyproject.toml`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,nlp1]"
```

The base project installs Pydantic. The `dev` extra installs pytest and
pytest-cov. The `nlp1` extra pins PyMuPDF 1.28.2 and Pillow 12.3.0.

There is no repository script or single command that restores Tesseract,
language packs, llama.cpp, the Qwen model, or the ignored NLP-3 response cache.
The NLP-1 report records the Tesseract package and official `tessdata_fast`
source URLs, while the model registry records the exact model/runtime versions
and hashes. Exact external-binary extraction/download commands could not be
verified from the repository. A new machine must provision these assets
manually and verify them with Section 5 before OCR or real-model work.

If the host Python 3.13 interpreter produces
`ModuleNotFoundError: No module named 'pymupdf'`, it is the wrong interpreter for
this repository. Use `.\.venv\Scripts\python.exe`. If PyMuPDF is also absent
there, restore the declared extras with the editable-install command above.

## 7. Quick sanity check

Normal regression command:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

Verified on 2026-10-14:

```text
302 passed, 2 skipped, 0 failed in 46.60s
```

The two skips are the two parameterized cases in
`tests/integration/test_nlp3_real_model.py`. They require the explicit opt-in
environment variable and a configured local model endpoint. A normal run must
not contact the model. Skipped opt-in tests are not failures; **zero failed** is
the health criterion. The `-p no:cacheprovider` option avoids the known Windows
permission warning for `.pytest_cache`.

## 8. Data / fixture map

The ten-document NLP-2 registry comprises the two NLP-1 files plus eight NLP-2
files. Provenance, source URLs, hashes, and redistribution caveats are in the
two `PROVENANCE.md` files.

| Milestone use | Language | File | Document type | Route | Purpose |
|---|---|---|---|---|---|
| NLP-1, NLP-2 | Hindi | `datasets/fixtures/nlp1/hindi/nfc_recruitment_01_2026_hindi.pdf` | Digital/searchable, 20 pages | Native | Real native ingestion |
| NLP-1, NLP-2 | Telugu | `datasets/fixtures/nlp1/telugu/ananthapuramu_anganwadi_recruitment_2025.pdf` | Scanned/image-only, 10 pages | Tesseract OCR | Real OCR ingestion |
| NLP-2 | Hindi | `datasets/fixtures/nlp2/hindi/du_ncweb_admission_2024_hindi.pdf` | Digital/searchable, 23 pages | Native | Admission baseline fixture |
| NLP-2 | Hindi | `datasets/fixtures/nlp2/hindi/kvs_admission_2025_hindi.pdf` | Image-only, 1 page | OCR required; native-only evaluator skips it | Admission fixture |
| NLP-2, NLP-3, NLP-4, NLP-5 | Hindi | `datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf` | Digital/searchable, 3 pages | Native | Scholarship/model/hybrid/QA smoke fixture |
| NLP-2 | Hindi | `datasets/fixtures/nlp2/hindi/uttarakhand_residential_school_exam_2025_hindi.pdf` | Image-only, 9 pages | OCR required; native-only evaluator skips it | Admission examination fixture |
| NLP-2, NLP-3, NLP-4, NLP-5 | Telugu/mixed | `datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf` | Digital/searchable, 4 pages | Native | Admission/model/hybrid/QA smoke fixture |
| NLP-2 | Telugu | `datasets/fixtures/nlp2/telugu/kv_kothuru_admission_2025_telugu.pdf` | Digital/searchable, 3 pages | Native | Admission baseline fixture |
| NLP-2 | Telugu | `datasets/fixtures/nlp2/telugu/kv_ramagundam_admission_2025_telugu.pdf` | Digital/searchable, 2 pages | Native | Admission baseline fixture |
| NLP-2 | Telugu | `datasets/fixtures/nlp2/telugu/tsemrs_admission_2024_telugu.pdf` | Image-only, 10 pages | OCR required; native-only evaluator skips it | Admission examination fixture |

The NLP-1 Telugu title transcription is
`datasets/fixtures/nlp1/ground_truth/telugu_page1_title.txt`.

## 9. NLP-1 reproduction

NLP-1 performs validation, SHA-256 identification, page-level routing, native
PyMuPDF extraction or rendered-page OCR, script labeling, and canonical
Document/Page/Block/Evidence construction.

Hindi native-PDF integration test:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\integration\test_nlp1_real_documents.py::test_real_hindi_digital_notice_uses_native_pdf
```

Concise, independently verified inspection command:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from services.nlp.ingestion import DocumentIngestor; r=DocumentIngestor().ingest(Path('datasets/fixtures/nlp1/hindi/nfc_recruitment_01_2026_hindi.pdf')); print({'document_id':r.document.document_id,'pages':r.document.page_count,'method':r.document.extraction_method,'blocks':sum(len(p.blocks) for p in r.document.pages),'evidence':len(r.evidence),'language':r.document.detected_language})"
```

Expected current summary: document ID beginning `2face8e0...`, 20 pages,
`native_pdf`, 390 blocks/evidence spans, language `hi`.

Telugu real-OCR integration test:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\integration\test_nlp1_real_documents.py::test_real_telugu_scanned_notice_runs_tesseract_and_retains_evidence
```

This test instantiates `TesseractBackend`, renders all ten pages at 250 DPI into
`.cache/nlp1-integration`, and performs real CPU OCR. Inspect the test and
`IngestionResult` for document ID/SHA-256, page count, route per page, block and
evidence counts, page numbers, normalized and original OCR text, bounding boxes,
confidence, script label, and stable evidence IDs. Success means the assertions
pass: all pages use Tesseract, readable text exceeds the smoke threshold,
geometry/original OCR text survive, confidence exists, and the manually
transcribed title remains within the tested CER/WER bounds.

## 10. NLP-1 OCR troubleshooting

| Symptom | Verification | Verified remedy or boundary |
|---|---|---|
| Tesseract executable missing | `.\.tools\Tesseract-OCR\tesseract.exe --version` | Restore the ignored local tool or set `TESSERACT_CMD` to an existing executable. Resolver order is explicit argument, `TESSERACT_CMD`, PATH, repo-local path, then `C:\Program Files\Tesseract-OCR\tesseract.exe`. |
| `tel`/`hin` missing | `.\.tools\Tesseract-OCR\tesseract.exe --list-langs` | Restore the corresponding official `tessdata_fast` `.traineddata` file under the selected Tesseract `tessdata` directory. |
| `ModuleNotFoundError: pymupdf` | `.\.venv\Scripts\python.exe -c "import pymupdf; print(pymupdf.__version__)"` | Use the repository `.venv`; if needed reinstall `.[dev,nlp1]`. |
| Corrupt/mismatched fixture | Compare the SHA-256 with `datasets/fixtures/nlp1/PROVENANCE.md` using `Get-FileHash` | Restore the tracked fixture from the correct Git checkpoint; do not alter it to make a test pass. |
| Empty OCR output | Run the Telugu integration test and inspect Tesseract stderr | The adapter raises `NoReadableTextError`; do not accept an empty document as success. Verify executable, language data, and source integrity. |

There is no verified automated external OCR installer in this repository.

## 11. NLP-2 reproduction

NLP-2 is `regex-baseline-nlp2-v1`, an interpretable baseline over NLP-1
ingestion. It emits canonical `NoticeAnalysis` plus service-only `RuleTrace`
diagnostics.

Run the real verified-complete native slice:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts\evaluate_nlp2.py
```

The script reads `datasets/annotations/nlp2/v1/annotations.json`, ingests all
registered fixtures, evaluates six native-readable documents, explicitly skips
four OCR-required files, and prints JSON to stdout. It does not create a report
file and has no CLI arguments.

Inspect category, notice number, authority, typed dates, fees/benefits,
documents, links, simple eligibility AST, actions, evidence IDs, warnings, and
stable rule trace IDs. The dedicated real-Hindi integration path is:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\integration\test_nlp2_real_documents.py
```

## 12. NLP-2 evaluation output

Only annotation fields marked `verified_complete` are scored. The verified
2026-10-14 rerun evaluated six documents and produced:

| Field | TP | FP | FN | Precision / Recall / F1 / EM |
|---|---:|---:|---:|---|
| Category | 6 | 0 | 0 | 1.000 / 1.000 / 1.000 / 1.000 |
| Notice number | 1 | 0 | 0 | 1.000 / 1.000 / 1.000 / 1.000 |
| Explicit zero-fee item | 1 | 0 | 0 | 1.000 / 1.000 / 1.000 / 1.000 |

These are smoke results on a tiny complete-label slice, not broad accuracy.
Partial/unverified/template-only fields cannot contribute gold metrics.

## 13. NLP-3 runtime architecture

NLP-3 uses the local Qwen checkpoint through an OpenAI-style llama.cpp HTTP
server and `ContextualStructuredExtractor`:

| Setting | Repository-verified value |
|---|---|
| Model file | `.tools\models\Qwen3-4B-Q4_K_M.gguf` |
| Model ID sent by client | `Qwen3-4B-Q4_K_M` |
| llama.cpp executable | `.tools\llama.cpp-b11429\llama-server.exe` |
| Base URL | `http://127.0.0.1:18089` |
| Chat endpoint used by provider | `/v1/chat/completions` |
| Health endpoint used historically | `http://127.0.0.1:18089/health` |
| Context size recorded | 16,384 |
| GPU layers recorded | all |
| Reasoning recorded | off |
| Flash attention recorded | auto |
| Prompt version | `indicnotice-contextual-v1` |
| Chunk limit | 3,000 characters |
| Max output | 4,096 tokens |
| Temperature / top-p / presence penalty / seed | 0.2 / 0.8 / 1.5 / 42 in `evaluate_nlp3.py` |
| Request timeout | 600 seconds |

The exact llama.cpp startup argument string, including flag spelling and any
thread count, is not present in Git history, scripts, milestone reports, or
configuration. **Exact command could not be verified from the repository.**
Do not infer it from the settings table.

## 14. Starting the NLP-3 model server

The repository verifies the executable, model, required endpoint, and runtime
settings, but does not contain a server launcher or the historical full launch
command. Therefore no startup command is supplied here.

**Exact command could not be verified from the repository.** Inspect
`.tools\llama.cpp-b11429\llama-server.exe --help`, the model/runtime table in
Section 13, and `scripts/evaluate_nlp3.py` before manually reconstructing a
launch procedure. Any reconstructed command must be recorded and independently
validated before it becomes authoritative.

For the 2026-10-14 pre-NLP-6 corrective rerun, the following command was
reconstructed from the installed binary's `--help` plus the verified settings
table. It is an audit record of that rerun, **not** the missing historical
command:

```powershell
.\.tools\llama.cpp-b11429\llama-server.exe --model ".\.tools\models\Qwen3-4B-Q4_K_M.gguf" --host 127.0.0.1 --port 18089 --ctx-size 16384 --n-gpu-layers all --flash-attn auto --reasoning off --no-webui
```

When a correctly configured server is already running, this verified health
check should return a healthy response:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:18089/health
```

A foreground server normally occupies its PowerShell terminal, so run the
evaluation from a second terminal. This describes the required operator layout;
it is not a claim about an unrecorded launch command.

## 15. Running NLP-3

With the server running—or with all exact request hashes already available in
the ignored `.tmp/nlp3_response_cache`—run:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_nlp3.py --output reports\nlp3_real_evaluation.json
```

Defaults are the Hindi SCERT Haryana NMMSS fixture and Telugu/mixed KVS Kadapa
fixture. The runner independently executes NLP-2 and NLP-3 on the same NLP-1
ingestion, writes `reports/nlp3_real_evaluation.json`, and records analyses,
chunks/attempts, repair behavior, raw model responses, schema validity,
evidence references/support, unsupported candidates, conflicts, timing, tokens,
model identity, and cache hits/misses.

The response cache is ignored by Git and is not available in a fresh clone.
Current local cache count is 22 files. A cache miss calls the configured
endpoint and performs expensive real inference.

Historical finding: Qwen was structurally integrated, but on the tiny
verified-complete subset category F1 was 0.500 versus NLP-2's 1.000 and fee F1
was 0.000 versus 1.000. Every chunk needed one repair. NLP-3 is experimental,
not production-ready.

## 16. Opt-in NLP-3 integration tests

The two skipped cases are the Hindi and Telugu parameterizations in
`tests/integration/test_nlp3_real_model.py`. Normal pytest skips them unless
`INDICNOTICE_RUN_NLP3_REAL` equals `1`.

After a local server is verified healthy, the repository-supported opt-in is:

```powershell
$env:INDICNOTICE_RUN_NLP3_REAL='1'
$env:INDICNOTICE_NLP3_BASE_URL='http://127.0.0.1:18089'
$env:INDICNOTICE_NLP3_MODEL_ID='Qwen3-4B-Q4_K_M'
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\integration\test_nlp3_real_model.py
```

The normal suite leaves the variable unset and historically reports 302 passed
and 2 skipped. The opt-in test performs fresh endpoint calls; it does not use
the evaluator's checkpoint cache.

## 17. Stopping the Qwen/llama.cpp server

No server lifecycle script or historical shutdown command is recorded.
**Exact command could not be verified from the repository.** If the server was
started interactively in a dedicated terminal, stop it through that owning
terminal's normal interrupt mechanism. Do not use broad `taskkill` or
`Stop-Process` commands from this runbook because the intended target and the
historical practice are not repository-verified.

## 18. NLP-4 reproduction

NLP-4 is `evidence-gated-semantic-nlp4-v1`. It re-ingests the two real fixtures,
runs NLP-2 independently, loads recorded NLP-3 analyses as untrusted contextual
candidates, and applies field-specific evidence and semantic promotion gates.
It does not run Qwen itself.

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_nlp4.py
```

Input defaults to `reports/nlp3_real_evaluation.json`; output defaults to
`reports/nlp4_real_evaluation.json`. Inspect each document's `nlp4_analysis`
and `gate_diagnostics`: proposed origin, promoted/rejected status, rejection
reason, evidence, conflicts, condition count, eligibility semantics, actions,
and dependencies. Historical diagnostic counts were 9 contextual candidates
promoted and 17 rejected. These are candidate counts, not accuracy metrics.

## 19. NLP-4 human-review data

The review queue is:

```text
datasets/annotations/nlp4/v1/semantic_examples.json
```

It contains 20 agent-prepared Hindi/Telugu semantic candidates. All 20 are
currently `NEEDS_HUMAN_VERIFICATION`; none is gold or scored. An AI agent must
not promote them to `VERIFIED`. See Sections 27-30 for the human workflow.

## 20. NLP-5 architecture

NLP-5 is `schema-first-grounded-qa-nlp5-v1`:

```text
question
  -> deterministic English/Hindi/Telugu intent routing
  -> canonical structured fact, deterministic eligibility, documents, or actions
  -> if unresolved, in-memory Unicode BM25 evidence retrieval
  -> cited extractive answer, partial answer, or NOT_STATED
```

Structured answers, deterministic eligibility, lexical retrieval, evidence
citations, abstention, and partial answers were tested. The optional bounded
generator adapter has fake-provider unit coverage only. NLP-5 did **not** run
real generative QA, and this runbook makes no generative QA quality claim.

## 21. Running NLP-5

Run the fixed real smoke set:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_nlp5.py
```

The script reads `reports/nlp4_real_evaluation.json` and writes
`reports/nlp5_real_qa.json`. Inspect each `real_smoke` entry for `question`,
`response.intent`, `answer_mode`, `answer_text`, `citations`, `abstained`,
`missing_information`, `eligibility_result`, citation validity, and ranked
retrieval spans/scores.

Historical smoke: eight real Hindi/Telugu cases; all eight had valid citations
or valid citation-free abstentions, including two abstentions. The 30 QA items
remain unverified, so this is execution evidence—not final QA accuracy.

## 22. Manual NLP-5 questions

Current NLP-5 reproduction uses the existing smoke/evaluation runner; there is
no standalone interactive chat CLI yet. `GroundedQAService.answer()` can be
called programmatically, and unit tests demonstrate deadline, fee, documents,
authority/application link, procedure, eligibility, partial, and unanswerable
questions, but the repository exposes no supported command-line question flag
or interactive API. Do not invent one.

## 23. One complete Hindi walkthrough

Use the SCERT Haryana NMMSS fixture for NLP-2 through NLP-5. NLP-1's dedicated
native smoke fixture is NFC; the contextual/hybrid/QA reports use SCERT.

1. Health and baseline:

   ```powershell
   .\.venv\Scripts\python.exe --version
   .\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
   ```

   Inspect Python 3.12.10 and zero failed tests.

2. NLP-1 native ingestion path:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\integration\test_nlp1_real_documents.py::test_real_hindi_digital_notice_uses_native_pdf
   ```

   Input is the NFC Hindi PDF; success proves the native document/evidence
   layer. The SCERT fixture is also natively ingested inside subsequent runners.

3. NLP-2 baseline:

   ```powershell
   $env:PYTHONUTF8='1'
   .\.venv\Scripts\python.exe scripts\evaluate_nlp2.py
   ```

   Input is the full registry; output is stdout. Inspect the SCERT analysis via
   the real integration test and baseline code; NLP-2 does not persist a JSON
   report.

4. Optional NLP-3 contextual experiment, only with a verified server or exact
   current response cache:

   ```powershell
   .\.venv\Scripts\python.exe scripts\evaluate_nlp3.py --fixture datasets\fixtures\nlp2\hindi\scert_haryana_nmmss_2025_hindi.pdf --output .tmp\runbook_hindi_nlp3.json
   ```

   Inspect the standalone NLP-3 analysis and diagnostics. It does not overwrite
   NLP-2. Fresh inference may take many minutes.

5. NLP-4 hybrid over that standalone candidate report:

   ```powershell
   .\.venv\Scripts\python.exe scripts\evaluate_nlp4.py --nlp3-report .tmp\runbook_hindi_nlp3.json --output .tmp\runbook_hindi_nlp4.json
   ```

   Inspect promotion/rejection decisions and the canonical hybrid analysis.

6. NLP-5 checked-in two-document smoke:

   ```powershell
   .\.venv\Scripts\python.exe scripts\evaluate_nlp5.py --input .tmp\runbook_hindi_nlp4.json --output .tmp\runbook_hindi_nlp5.json
   ```

   NLP-5 indexes records by `document_id`, so multiple notices sharing a
   language are preserved. Inspect `hi-*` cases in the selected output.

## 24. One complete Telugu walkthrough

1. Verify the OCR binary and languages:

   ```powershell
   .\.tools\Tesseract-OCR\tesseract.exe --version
   .\.tools\Tesseract-OCR\tesseract.exe --list-langs
   ```

2. Run real NLP-1 Tesseract OCR on the ten-page Anganwadi scan:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\integration\test_nlp1_real_documents.py::test_real_telugu_scanned_notice_runs_tesseract_and_retains_evidence
   ```

   This invokes actual Tesseract at 250 DPI. Visually/semantically inspect raw
   versus normalized OCR text, Telugu glyph corruption, Latin noise, page
   ordering, bboxes, confidence, and the page-1 title transcription. Do not
   silently correct OCR text.

3. Run the NLP-2 registry evaluation:

   ```powershell
   $env:PYTHONUTF8='1'
   .\.venv\Scripts\python.exe scripts\evaluate_nlp2.py
   ```

   The native-only evaluator skips the image-only Anganwadi file but evaluates
   the searchable Telugu fixtures, including KVS Kadapa. This limitation is
   explicit in stdout.

4. Optionally run standalone NLP-3 on KVS Kadapa:

   ```powershell
   .\.venv\Scripts\python.exe scripts\evaluate_nlp3.py --fixture datasets\fixtures\nlp2\telugu\kv_kadapa_admission_2025_telugu.pdf --output .tmp\runbook_telugu_nlp3.json
   ```

5. Run NLP-4 over that Telugu candidate report:

   ```powershell
   .\.venv\Scripts\python.exe scripts\evaluate_nlp4.py --nlp3-report .tmp\runbook_telugu_nlp3.json --output .tmp\runbook_telugu_nlp4.json
   ```

6. Run the fixed NLP-5 smoke and inspect `te-*` cases:

   ```powershell
   .\.venv\Scripts\python.exe scripts\evaluate_nlp5.py
   ```

NLP-2, NLP-3, and NLP-4 outputs remain distinct experimental variants.

## 25. Experimental method map

| Stage | Input | Method | Relationship |
|---|---|---|---|
| NLP-1 | PDF/image | Native extraction or OCR into document/evidence | Shared document layer |
| NLP-2 | NLP-1 result | Deterministic rules/regex | Academic baseline |
| NLP-3 | Same NLP-1 result | Standalone contextual Qwen extraction | Compared independently with NLP-2 |
| NLP-4 | Fresh NLP-1 + NLP-2 + recorded NLP-3 candidates | Evidence-gated semantic hybrid | Separate hybrid method; preserves comparison |
| NLP-5 | Canonical NLP-4 analysis/evidence | Structured QA, deterministic eligibility, lexical retrieval, abstention | Downstream interaction layer |

NLP-2 versus NLP-3 is the baseline/contextual comparison. NLP-4 is not a
renamed NLP-3 output; it gates contextual candidates against evidence and
deterministic semantics. NLP-5 answers only from canonical facts or evidence.

## 26. Output artifact map

| Stage | Command/script | Input | Primary output | Contents |
|---|---|---|---|---|
| NLP-1 | `tests/integration/test_nlp1_real_documents.py` | NLP-1 Hindi/Telugu fixtures | Test result and in-memory `IngestionResult`; no committed run JSON | Document/pages/blocks, routes, evidence, OCR geometry/confidence |
| NLP-2 | `scripts/evaluate_nlp2.py` | Fixture/annotation registry | JSON on stdout; no report file | Verified-only field metrics, errors, explicit OCR skips |
| NLP-3 | `scripts/evaluate_nlp3.py` | SCERT + KVS Kadapa by default | `reports/nlp3_real_evaluation.json` | NLP-2/NLP-3 analyses, grounding, raw attempts, model/runtime data |
| NLP-4 | `scripts/evaluate_nlp4.py` | NLP-3 report plus fresh ingestion | `reports/nlp4_real_evaluation.json` | Hybrid analyses, gates, rejections, conflicts, ablation counts |
| NLP-5 | `scripts/evaluate_nlp5.py` | NLP-4 report | `reports/nlp5_real_qa.json` | Eight QA responses, citations, retrieval scores, abstentions |

Human-readable checkpoints are `NLP1_MILESTONE_REPORT.md` through
`NLP5_MILESTONE_REPORT.md`; NLP-0 is summarized in `NLP0_FINAL_AUDIT.md`.

## 27. Human review workflow

Review these files manually; do not ask an AI agent to promote labels:

```text
datasets/annotations/nlp4/v1/semantic_examples.json
datasets/annotations/nlp5/v1/qa_examples.json
```

The prompt requesting this runbook named five conceptual review outcomes, but
the checked-in schemas do not share those five values. Repository-valid states
are:

| Conceptual outcome | NLP-4 schema representation | NLP-5 schema representation |
|---|---|---|
| `NEEDS_HUMAN_VERIFICATION` | Valid | Valid |
| `VERIFIED` | Valid | Valid |
| `CORRECTED_AND_VERIFIED` | Not an enum value; correct the candidate, then use `VERIFIED` and record correction externally | Same |
| `REJECTED` | Valid | Not an enum value; rejection requires a schema/workflow decision before editing |
| `UNCERTAIN` | Not an enum value; leave `NEEDS_HUMAN_VERIFICATION` | Use `UNVERIFIED` or leave `NEEDS_HUMAN_VERIFICATION`, according to the human review protocol |

NLP-5 additionally permits `UNVERIFIED`. This discrepancy is documented here
rather than changing schemas during a documentation-only task. Only a real
human reviewer may set `VERIFIED`. Record reviewer ID, date, rationale, and
corrections in a separate review log until the project formally adds review
metadata fields.

## 28. NLP-4 semantic review checklist

For every semantic example, the human reviewer must verify:

- source document ID and language;
- page/block and exact evidence span;
- normalized attribute, comparator, value, and unit;
- AND/OR nesting and alternatives;
- guards, applicability, relaxations, and exemptions;
- reference/cutoff date;
- action type, action evidence, dependencies, parallelism, optionality, and
  conditionality;
- whether “preference” or “desirable” wording was incorrectly promoted into a
  mandatory rule.

Illustrations:

- “income below ₹3 lakh” means `< 300000`, not `<= 300000`.
- “75% or above” means `>= 75`.
- “B.Tech or B.E.” is an OR group, not AND.
- “preference will be given” must not automatically become mandatory
  eligibility.
- A relaxation must have a supported base limit and an applicable category
  guard; missing category information should remain UNKNOWN.

## 29. NLP-5 QA review checklist

For each QA item, verify:

- question text, question language, fixture, notice language, and document ID;
- intended question type and canonical source field, if any;
- expected answerability: `ANSWERABLE`, `PARTIAL`, or `UNANSWERABLE`;
- candidate answer wording and every critical number/date/URL;
- every cited evidence ID, page, block, and semantic support;
- whether abstention is required;
- whether a compound question is only partially answered;
- deterministic PASS/FAIL/UNKNOWN result for eligibility cases;
- exact missing profile attributes, with no unrelated fields requested.

An `UNANSWERABLE` decision must be checked against the whole relevant notice,
not only the cited page or top retrieval result. Citation existence alone does
not establish semantic support.

## 30. Human review examples

Do not paste the following workflow record into an annotation file; it is an
illustrative external review-log shape because `reviewer` and correction
outcomes are not fields in the current annotation schemas.

```json
{
  "item_id": "example_or_qa_id",
  "review_outcome": "CORRECTED_AND_VERIFIED",
  "annotation_verification_state": "VERIFIED",
  "reviewer": "reviewer_1",
  "notes": "Changed <= to < after checking the cited source text."
}
```

- VERIFIED: source, semantics/answer, and evidence are correct without edits;
  set the annotation's `verification_state` to `VERIFIED`.
- CORRECTED_AND_VERIFIED: the human corrects the candidate fields, records the
  correction externally, then sets repository state to `VERIFIED`.
- REJECTED: the semantic candidate is unsupported; NLP-4 can use `REJECTED`.
  NLP-5 has no `REJECTED` enum and must not receive that value without an
  approved schema change.
- UNCERTAIN: evidence is insufficient or ambiguous; do not set `VERIFIED`.
  Preserve `NEEDS_HUMAN_VERIFICATION` or use the dataset's existing
  `UNVERIFIED` state where the human protocol calls for it.

## 31. JSON validation after human review

Use the verified repository interpreter for JSON validation:

```powershell
.\.venv\Scripts\python.exe -m json.tool datasets\annotations\nlp4\v1\semantic_examples.json > $null
.\.venv\Scripts\python.exe -m json.tool datasets\annotations\nlp5\v1\qa_examples.json > $null
```

No output and exit code 0 means JSON syntax is valid. This does not validate
the typed review models or semantic correctness; run
`tests\unit\test_review_datasets.py` for those checks.

## 32. Tests after human review

After any human annotation edits, rerun:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

The durable criterion is **0 failed**, not a permanent exact count of 302;
future tests may raise the pass count. Expected opt-in model skips remain
acceptable in the normal run.

## 33. Committing human-verified data

Do not commit review data until JSON validation and the full suite pass. Then a
human operator may run:

```powershell
git status --short
git add -- datasets/annotations/nlp4/v1/semantic_examples.json datasets/annotations/nlp5/v1/qa_examples.json
git diff --cached --check
git diff --cached -- datasets/annotations/nlp4/v1/semantic_examples.json datasets/annotations/nlp5/v1/qa_examples.json
git commit -m "Human verify NLP-4 semantic and NLP-5 QA annotations"
```

These commands were not run while generating this runbook.

## 34. Common failure modes

| Symptom | Likely cause | How to verify | Verified remedy/boundary |
|---|---|---|---|
| `ModuleNotFoundError: pymupdf` | Host Python 3.13 used instead of `.venv`, or extras missing | Print `sys.executable`; import with `.venv` | Use `.venv\Scripts\python.exe`; restore `.[dev,nlp1]` if needed |
| Tesseract executable unavailable | Ignored `.tools` asset absent and no system/path override | Run repo-local `tesseract.exe --version` | Restore the known local binary or set `TESSERACT_CMD` to a verified executable |
| OCR language unavailable | `tel`, `hin`, or `eng` traineddata absent | `tesseract.exe --list-langs` | Restore official language data in selected `tessdata` |
| Qwen server unavailable / connection refused | llama.cpp not running at base URL | `Invoke-RestMethod` against `/health` | Start the correctly configured local server; exact launch command is not recoverable from repository |
| Wrong model path or hash | Ignored model absent/replaced | `Get-FileHash` and compare Section 4 | Restore exact `Qwen3-4B-Q4_K_M.gguf`; do not substitute silently |
| Opt-in integration tests skipped | `INDICNOTICE_RUN_NLP3_REAL` is not `1` | Inspect skip reason/test file | Expected for normal run; set supported variables only when server is healthy |
| Fixture missing/corrupt | Incomplete checkout or local alteration | `git status`; `Get-FileHash`; provenance table | Restore tracked fixture from Git; do not edit source PDF |
| Python version mismatch | Host `python` used | `python --version` and `.venv\Scripts\python.exe --version` | Use repository Python 3.12.10 |
| Malformed annotation JSON | Manual comma/quote/bracket error | Section 31 commands | Correct syntax, then rerun tests; do not auto-promote labels |
| Dirty worktree | Generated output or unrelated edits present | `git status --short` | Identify ownership and intended changes; do not reset blindly |
| NLP-3 unexpectedly calls model | Missing request-hash cache entry | Inspect `runtime.checkpoint_cache` in output | Ensure server is running or restore exact local cache; cache is ignored and non-portable |

## 35. Important “do not” list

- Do not casually edit frozen NLP-0/schema 1.0 contracts.
- Do not replace the Qwen checkpoint while claiming reproduction.
- Do not change prompts, chunk sizes, decoding, or gates before locked final
  evaluation.
- Do not promote AI-generated semantic/QA labels to `VERIFIED` without human
  review.
- Do not call expected opt-in skips failures.
- Do not describe NLP-3 as production-ready or quality-superior.
- Do not claim real generative QA was tested; it was not.
- Do not invent benchmark metrics from smoke outputs.
- Do not overwrite evidence or annotations to make predictions appear correct.
- Do not treat NLP-2/NLP-3/NLP-4 as one overwriting pipeline.
- Do not begin NLP-6 until the review prerequisites below are satisfied.

## 36. Before NLP-6 checklist

- [ ] Git working tree understood and clean for the intended checkpoint
- [ ] Repository Python environment verified
- [ ] Full regression suite has 0 failures
- [ ] One Hindi pipeline smoke manually reproduced
- [ ] One Telugu pipeline smoke manually reproduced, including actual OCR
- [ ] NLP-3 optional model-server/cache behavior understood
- [ ] NLP-4 semantic review completed by humans
- [ ] NLP-5 QA review completed by humans
- [ ] Both annotation JSON files validate
- [ ] Annotation review changes committed
- [ ] Final VERIFIED / rejected-or-unverified / uncertain counts recorded using repository-valid states

## 37. Quick reproduction cheat sheet

The Qwen launch command is deliberately absent because it could not be verified.
All commands below are repository-backed and were verified or recorded by the
milestone runners.

```powershell
Set-Location -LiteralPath (git rev-parse --show-toplevel)

git status --short
git log --oneline --decorate -5

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import pymupdf; print(pymupdf.__version__)"
.\.tools\Tesseract-OCR\tesseract.exe --version
.\.tools\Tesseract-OCR\tesseract.exe --list-langs

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q tests\integration\test_nlp1_real_documents.py

$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts\evaluate_nlp2.py

Invoke-RestMethod -Uri http://127.0.0.1:18089/health
.\.venv\Scripts\python.exe scripts\evaluate_nlp3.py --output reports\nlp3_real_evaluation.json

.\.venv\Scripts\python.exe scripts\evaluate_nlp4.py
.\.venv\Scripts\python.exe scripts\evaluate_nlp5.py

.\.venv\Scripts\python.exe -m json.tool datasets\annotations\nlp4\v1\semantic_examples.json > $null
.\.venv\Scripts\python.exe -m json.tool datasets\annotations\nlp5\v1\qa_examples.json > $null
```

If the health check fails, do not run fresh NLP-3 inference. Sections 13-17
explain the verified model boundary and the missing historical launch command.

## 38. Final human-review gate

Generate or refresh the read-only review packet:

```powershell
.\.venv\Scripts\python.exe scripts\build_final_human_review.py
```

Review these files against the original PDFs and synthetic-case intent:

- `reports/final_human_review/qa_review.md` — 30 real-notice QA candidates;
- `reports/final_human_review/semantic_review.md` — 20 synthetic semantic cases;
- `reports/final_human_review/profile_review.md` — 13 executable profile cases;
- `reports/final_human_review/review_summary.json` — counts and non-binding AI suggestions.

`READY_TO_VERIFY` is not a verification state. A human must explicitly decide
every selected item. Exclude `hi-q15` from scored gold because its minimum-marks
wording has multiple valid interpretations. Do not rewrite it into an easier
scored question and do not verify the existing ambiguous wording.

The optional one-item-at-a-time helper has no default verify action:

```powershell
.\.venv\Scripts\python.exe scripts\review_final_annotations.py qa --id hi-q01
.\.venv\Scripts\python.exe scripts\review_final_annotations.py semantic --id hi-01
```

It creates a timestamped backup, validates the complete JSON, changes only the
selected record's `verification_state`, and records the explicit action in
`reports/final_human_review/human_review_log.jsonl`. `SKIP` maps to `REJECTED`;
Enter or `LEAVE UNVERIFIED` changes nothing.

After completing review, rerun this finalization workflow so it can create the
verified-only NLP-6 manifest. Until that manifest exists, this command must fail:

```powershell
.\.venv\Scripts\python.exe scripts\validate_nlp6_gold.py
```

Only `PASS — NLP6 GOLD FREEZE VALID` authorizes final NLP-6 scoring.

## 39. Professor-facing Streamlit demo

Install the optional dependency without changing core runtime dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[demo]"
```

Start the demo:

```powershell
.\.venv\Scripts\python.exe -m streamlit run demo\app.py
```

The seven tabs cover overview, dates/fees, nested eligibility, conditional
documents and procedure, deterministic candidate checking, grounded QA, and
evidence/research diagnostics. The NLP-3 mode requires the configured local
OpenAI-compatible Qwen server. NLP-2 remains available offline. NLP-4 continues
with deterministic extraction plus semantic rules when Qwen is offline and
states clearly that no contextual candidates were supplied.

## 40. Finalization verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
git diff --check
git status --short
```

Do not run final NLP-6 metrics, create `reports/nlp6/`, or make final performance
claims while required selected annotations remain unverified.

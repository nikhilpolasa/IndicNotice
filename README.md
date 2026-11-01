# IndicNotice

IndicNotice helps students understand public scholarship, admission, examination, and recruitment notices. It ingests PDF notices, extracts facts with links to page evidence, answers supported questions in English, Telugu, and Hindi, and compares published notices with a student profile. It is an academic project; extracted information should be checked against the original notice.

## Features and current status

- Native PDF text extraction and optional Tesseract OCR for scanned PDFs.
- Structured dates, fees, documents, eligibility conditions, and application steps with source evidence.
- Multilingual notice questions with citations and abstention when a fact is not stated.
- Deterministic eligibility results: PASS, FAIL, UNKNOWN, and NOT_APPLICABLE. Missing or unreviewed requirements cannot produce an unconditional eligibility guarantee.
- Local registration and sign-in, student profiles, admin notice review and publication, personalized notice discovery, and in-app notifications.
- Research pipelines, schemas, datasets, annotations, evaluation tools, and reproducibility notes remain part of the repository.

Version 2C is implemented. The latest recorded regression run was 438 passed and 2 skipped; the final manual acceptance gate remains partial. In particular, the full multilingual question-answering browser matrix and notification/read-state persistence across an application process restart were not completely demonstrated. The previous QA record did not fully demonstrate the multilingual question-answering browser matrix or notification/read-state persistence across an application process restart; both remain open manual acceptance items.

## How the NLP flow works

1. The ingestion router validates a PDF or image and extracts native PDF text where available. Scanned pages use Tesseract when installed.
2. The baseline extractor builds the canonical `NoticeAnalysis` schema and attaches evidence spans and page numbers to supported values.
3. Deterministic validators and eligibility rules preserve unknown values instead of filling gaps with guesses.
4. Grounded question answering uses notice evidence; unsupported questions receive an abstention.
5. Optional contextual review can run separately against a configured local model. It does not participate in the normal fast initial-analysis path and is not needed to install or use the standard reader.

See [`docs/`](docs/) and [`demo/README.md`](demo/README.md) for the research architecture and reader behavior.

## Architecture

```text
PDF or image
  -> ingestion (native PDF text, or optional Tesseract OCR)
  -> structured extraction and validation
  -> canonical notice schema with evidence spans
  -> grounded questions and deterministic eligibility

Browser -> authenticated FastAPI gateway -> private Streamlit worker
                                      -> local SQLite account/notice/notification store
```

The gateway owns registration, sign-in, authorization, and the local SQLite store. The Streamlit worker is bound to loopback and should be launched through the gateway. The normal reader does not call an AI model.

## Prerequisites

- Python 3.11 or newer (Python 3.12 is used by the project runbook).
- Git.
- Tesseract OCR 5 with `eng`, `hin`, and `tel` language data only if you need scanned Hindi/Telugu/English documents. Native-text PDFs do not require Tesseract.
- A local Qwen-compatible model server only for optional contextual research review. This is not required by the normal product workflow.

## Install on Windows PowerShell

From the repository root, create a local environment and install the application, UI, OCR/PDF, authentication, and development dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,nlp1,demo,auth]"
```

Install Tesseract separately using your operating system's package manager or a trusted Tesseract distribution. Ensure its `tessdata` includes `eng`, `hin`, and `tel`. If `tesseract.exe` is not on `PATH`, set `TESSERACT_CMD` in the current PowerShell session to its executable path, for example:

```powershell
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
& $env:TESSERACT_CMD --list-langs
```

Do not put personal paths or secrets in tracked source files. The `api` dependency extra is for the separate research API and is not needed for the Streamlit reader.

## Local database and authenticated application

The application uses SQLite. Database migrations run when the auth store initializes. By default, account and notice data live under the ignored `.data/` directory. To isolate a developer's data, choose a dedicated local database path before launching:

```powershell
$env:INDICNOTICE_AUTH_DB = (Join-Path (Get-Location) '.data\local\indicnotice.sqlite3')
.\.venv\Scripts\python.exe -m services.auth.launch
```

Open <http://127.0.0.1:8501>. Keep the server running in that terminal. `INDICNOTICE_AUTH_PORT` and `INDICNOTICE_STREAMLIT_PORT` can change the gateway and private worker ports. The gateway binds to loopback by default. Do not expose the development server directly to the public internet. HTTPS deployments must configure the public origin, allowed host names, and secure cookies as described in [`demo/README.md`](demo/README.md).

### Administrator setup

Register an account through the application first. Then, from another terminal, set the same `INDICNOTICE_AUTH_DB` value used by the server and run the operator command for that existing account:

```powershell
$env:INDICNOTICE_AUTH_DB = (Join-Path (Get-Location) '.data\local\indicnotice.sqlite3')
.\.venv\Scripts\python.exe -m services.auth.admin promote --email admin@example.org
```

The command asks you to type `PROMOTE`, then prompts for the existing account password without echoing it. Do not put passwords in source code, command arguments, issue reports, or chat. Promotion authenticates the existing account; it does not create a default administrator.

## Analyze a notice

1. Sign in and open the notice reader.
2. Upload a PDF through the interface and choose English, Telugu, or Hindi for the task view.
3. Review the extracted facts and their page evidence against the original PDF.
4. Ask questions whose answers can be supported by the notice. Check the citations; the system should abstain when a fact is absent.
5. Treat eligibility as a source-based assessment, not an official decision. Incomplete requirement coverage remains qualified or unknown.

The checked-in real document fixtures under `datasets/fixtures/` support reproducible development and tests. Do not add private applicant records or uploaded user notices as fixtures.

## Tests and research tools

Run the full regression suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Useful focused checks include `tests/unit`, `tests/integration`, and `tests/evaluation`. Some integration tests skip when an optional native tool or external local model is unavailable. The Qwen real-model evaluation is explicitly opt-in; consult [`docs/RUNBOOK.md`](docs/RUNBOOK.md) before running research benchmarks. Do not change gold annotations or evaluation methodology without an independently reviewed research change.

Optional native-text performance benchmark:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_product.py
```

Scanned-document OCR performance is separate from the native-text target.

## Optional Qwen research review

The standard install and normal initial analysis do not require a model download. Advanced review can use a locally managed Qwen-compatible server. Keep model weights and server binaries in ignored local storage such as `.tools/`; do not commit downloaded GGUF files. Configure `INDICNOTICE_MODEL_URL` and `INDICNOTICE_MODEL_ID` in the process environment and follow [`demo/README.md`](demo/README.md) for the server setup and limits. Optional model review may be slow or unavailable; the baseline analysis remains usable.

## In-app notifications and deadline reminders

Published notices may create account-scoped in-app notifications. There is no email or push delivery. Deadline reminders are not automatically scheduled by the application. Configure a daily Windows Task Scheduler or host scheduler action that runs, from the repository root, with the same `INDICNOTICE_AUTH_DB` value as the app:

```powershell
.\.venv\Scripts\python.exe -m services.auth.notifications
```

The job uses `Asia/Kolkata` by default and is idempotent. See [`demo/README.md`](demo/README.md) for details.

## Privacy and local files

`.gitignore` excludes virtual environments, `.tools/`, `.data/`, SQLite databases, local secrets, caches, build outputs, and test runtime files. Review `git status --ignored` before sharing a machine or creating a release. Never commit `.env` files with secrets, account databases, uploaded PDFs, browser profiles/cookies, logs, PID files, or model weights. Ignore rules do not remove files already tracked; inspect the staged file list before committing.

## Collaboration

Use a short-lived feature branch and a pull request for every change. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the team workflow and review checklist.

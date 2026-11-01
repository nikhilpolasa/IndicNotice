# IndicNotice notice reader

Run from the existing repository root. Authentication and private profiles are
served by the same-origin gateway; start the application through the launcher
instead of starting the Streamlit worker directly:

```powershell
.\.venv\Scripts\python.exe -m services.auth.launch
```

Open `http://127.0.0.1:8501`. The Streamlit worker listens only on
`127.0.0.1:8502` and is reachable through the authenticated gateway. To use a
different persistent database location, set `INDICNOTICE_AUTH_DB` before
launching. For deployment behind HTTPS, set `INDICNOTICE_AUTH_COOKIE_SECURE=true`
and configure `INDICNOTICE_AUTH_ORIGIN` and `INDICNOTICE_AUTH_ALLOWED_HOSTS` to
the public origin and host names.

Install optional UI dependencies only if they are missing:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[demo,nlp1,dev,auth]"
```

Upload an English, Telugu or Hindi PDF, choose a display language, and select
**Analyze notice**. The eight task views expose the overview, dates, fees and
application steps, documents, eligibility rules, profile check, notice questions,
and source passages. Quotes and proper names retain their source language.

Initial analysis uses the existing baseline extractor and evidence-gated semantic
rules. It makes no model calls and is explicitly incomplete. Matching these
initial rules cannot produce a confident overall Eligible result. Missing profile
values remain unknown. The original evaluator and its four states are preserved.

**Run advanced review** starts an optional background job over the already parsed
text, focused on eligibility, required documents and application steps. Dates,
fees and metadata remain from initial extraction. The reader remains usable. A
two-minute total request budget covers every
chunk. The production profile disables model repair calls: unsupported claims are
rejected with the same existing deterministic validation and semantic gates;
invalid JSON fails safely. Source quotations are bounded to 320 characters, while
complete source evidence remains available. These limits can leave facts unresolved.
The research extractor still defaults to one repair and its original full prompt.
A failed or timed-out review leaves the initial result and its status intact.
Advanced results can still contain unresolved information; always inspect sources.

## Optional local model

The checked-in provider defaults are used privately. Override them using
`INDICNOTICE_MODEL_URL` and `INDICNOTICE_MODEL_ID` environment variables.
No credentials, model controls or endpoint URLs appear in the interface.

## In-app notifications and reminders

Published notices create idempotent in-app events for users whose saved profiles
meet reviewed, cited requirements. Incomplete or unreviewed matches only create
“More information needed” events when the user enables that preference. No email
or push delivery is configured. Deadline reminders are created by a daily job;
run this command once per day through Windows Task Scheduler or the host's
equivalent scheduler:

```powershell
.\.venv\Scripts\python.exe -m services.auth.notifications
```

The job uses the `INDICNOTICE_AUTH_DB` configured for the application, defaults
to `Asia/Kolkata`, and is idempotent. It only considers supported,
evidence-cited future application deadlines on currently published notices.
Notification reads and preferences are stored per account in SQLite.

On the inspected machine, Vulkan0 is Intel integrated graphics and Vulkan1 is the
RTX 4060. Confirm device ordering with `llama-server.exe --list-devices` on other
machines. The tested server command is:

```powershell
.\.tools\llama.cpp-b11429\llama-server.exe -m .tools/models/Qwen3-4B-Q4_K_M.gguf --device Vulkan1 -ngl 99 -c 16384 --parallel 1 --host 127.0.0.1 --port 8080 --reasoning off --jinja
```

The benchmarks use a 16K context. Earlier full-extraction trials exceeded an 8K
context. The production requirements review uses compact evidence headers and
5000-character chunks; all evidence text and canonical citations are preserved.
Generation is bounded to 4096 tokens per request. Full contextual extraction
does not meet the initial-analysis latency
target. Multiple simultaneous reviews can queue at a single-slot model server.

## Privacy and errors

PDF uploads and rendered OCR images use temporary directories and are deleted
after ingestion, including failures. One content-hash cache lives in each
Streamlit session; there is no global document or candidate cache. Changing the
upload clears the previous result, question, profile and form values. Clearing
also removes the upload widget's data. A running advanced HTTP request may finish
in the background within its timeout after clearing, but its result is discarded.
Profile values are never sent to the model. Internal failures are logged; the
public UI shows localized errors and Streamlit error details are disabled.

Scanned PDFs require installed Tesseract and the eng/hin/tel language packs.
Native-text pages never run OCR. OCR latency is outside the native-PDF target.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/benchmark_product.py
.\.venv\Scripts\python.exe scripts/benchmark_advanced.py
```

Native benchmarks run each fixture in a fresh Python process, then measure warm
uncached and same-session cached calls separately. They do not flush operating
system disk caches. Use `--include-ocr` to include scanned fixtures.

`scripts/browser_product.py` drives a real Chrome browser through CDP using the
already installed `websockets` package. It requires the application on port 8501
and a dedicated headless Chrome profile with remote debugging on port 9223.
It tests real uploads, languages, questions, source citations, profile unknowns,
session isolation, clearing, mobile layout and safe invalid-file errors.

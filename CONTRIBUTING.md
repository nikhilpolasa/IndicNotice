# Contributing to IndicNotice

Thanks for helping improve IndicNotice. Keep changes reviewable and preserve the project's source-grounded behavior and research provenance.

## Start a change

1. Clone the private repository and create your own local Python environment using the install steps in `README.md`.
2. Update your local `main` branch, then create a focused feature branch (for example, `feature/notice-export` or `fix/telugu-date-parser`).
3. Keep each change focused. Do not include local SQLite files, uploaded notices, profiles, secrets, browser state, logs, caches, or downloaded model files.
4. Add or update tests for behavior changes. Keep the full regression suite green where practical.
5. Open a pull request against `main`, explain the user impact, implementation, test results, and any known limitations.
6. Request review and address feedback before merging. Do not push directly to `main` unless repository maintainers explicitly authorize an exception.

## Before opening a pull request

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git status --short
```

Inspect `git diff` and the staged file list. Do not alter gold annotations or evaluation methodology as part of an unrelated feature. Research and product changes should keep citations, eligibility uncertainty, and user-data isolation intact.

## Pull request review

A pull request should include a concise summary, test commands and results, screenshots for user-facing changes where safe, migration notes when needed, and unresolved limitations. Reviewers should check access control, account isolation, database migration behavior, source citations, and whether errors are surfaced safely.

Never paste passwords, tokens, session keys, private PDFs, or applicant data into commits, issues, or pull requests.

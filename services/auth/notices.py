"""Persistent published-notice storage and deterministic personalized matches."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Iterable
from uuid import uuid4

from indicnotice.schemas.eligibility import Condition, ConditionGroup, EvalStatus
from indicnotice.schemas.notice import NoticeAnalysis
from services.auth.store import AuthStore, AuthorizationError, utc_now
from services.nlp.eligibility.evaluator import evaluate_eligibility
from services.nlp.eligibility.explanations import EligibilityExplanation, explain_eligibility
from services.nlp.semantic.canonical import iter_conditions


class DuplicateNotice(ValueError):
    def __init__(self, notice_id: str):
        super().__init__("This PDF is already present in the notice library.")
        self.notice_id = notice_id


class NoticeUnavailable(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class NoticeRecord:
    notice_id: str
    document_sha256: str
    storage_key: str
    owner_id: str | None
    title: str
    issuing_authority: str | None
    source_url: str | None
    source_language: str | None
    publication_date: str | None
    deadlines: tuple[dict, ...]
    publication_state: str
    eligibility_reviewed: bool
    eligibility_reviewed_by: str | None
    eligibility_reviewed_at: str | None
    uploaded_at: str
    updated_at: str
    published_at: str | None
    analysis: NoticeAnalysis


@dataclass(frozen=True, slots=True)
class MatchResult:
    notice: NoticeRecord
    status: str
    evaluation: object
    explanation: EligibilityExplanation
    coverage_complete: bool


def _row_record(row: sqlite3.Row) -> NoticeRecord:
    return NoticeRecord(
        notice_id=row["notice_id"], document_sha256=row["document_sha256"],
        storage_key=row["storage_key"], owner_id=row["owner_id"], title=row["title"],
        issuing_authority=row["issuing_authority"], source_url=row["source_url"],
        source_language=row["source_language"], publication_date=row["publication_date"],
        deadlines=tuple(json.loads(row["deadlines_json"])),
        publication_state=row["publication_state"],
        eligibility_reviewed=bool(row["eligibility_reviewed"]),
        eligibility_reviewed_by=row["eligibility_reviewed_by"],
        eligibility_reviewed_at=row["eligibility_reviewed_at"],
        uploaded_at=row["uploaded_at"], updated_at=row["updated_at"],
        published_at=row["published_at"],
        analysis=NoticeAnalysis.model_validate_json(row["analysis_json"]),
    )


def has_supported_review_coverage(notice: NoticeRecord) -> bool:
    """Require an admin completeness review and page evidence for every rule."""
    if not notice.eligibility_reviewed or not has_reviewable_eligibility_coverage(notice.analysis):
        return False
    return True


def has_reviewable_eligibility_coverage(analysis: NoticeAnalysis) -> bool:
    """Whether an analysis can safely accept the admin completeness attestation."""
    if analysis.eligibility is None:
        return False
    conditions = list(iter_conditions(analysis.eligibility))
    if not conditions:
        return False
    evidence_ids = analysis.evidence_ids()
    for condition in conditions:
        if condition.review_state.value in {"needs_review", "rejected"}:
            return False
        if condition.confidence < 0.75:
            return False
        if not condition.evidence_ids or any(item not in evidence_ids for item in condition.evidence_ids):
            return False
    if any(warning.severity == "error" or "eligibility" in (warning.field_path or "").casefold()
           for warning in analysis.warnings):
        return False
    return True


def evaluate_notice(notice: NoticeRecord, profile: dict[str, object]) -> MatchResult:
    """Re-evaluate a profile on demand; no cross-user or stale match cache exists."""
    evaluation = evaluate_eligibility(profile, notice.analysis.eligibility)
    explanation = explain_eligibility(profile, notice.analysis.eligibility, notice.analysis.evidence)
    coverage = has_supported_review_coverage(notice)
    if evaluation.overall == EvalStatus.FAIL:
        status = "does_not_meet"
    elif evaluation.overall == EvalStatus.PASS and coverage:
        status = "reviewed_requirements_met"
    elif evaluation.overall == EvalStatus.PASS:
        status = "requirements_met_so_far"
    else:
        status = "needs_information"
    return MatchResult(notice, status, evaluation, explanation, coverage)


class NoticeLibrary:
    def __init__(self, store: AuthStore):
        self.store = store
        self.database_path = store.database_path
        db_parent = Path(database_path_parent(store.database_path))
        self.storage_dir = db_parent / "notices"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.storage_dir.chmod(0o700)

    @staticmethod
    def _require_admin(connection: sqlite3.Connection, account_id: str) -> None:
        row = connection.execute("SELECT is_admin FROM accounts WHERE account_id=?", (account_id,)).fetchone()
        if not row or not row["is_admin"]:
            raise AuthorizationError("Administrator privileges are required.")

    def create_draft(self, account_id: str, pdf_bytes: bytes, analysis: NoticeAnalysis,
                     title: str | None = None) -> NoticeRecord:
        if not pdf_bytes.startswith(b"%PDF-") or len(pdf_bytes) > 50 * 1024 * 1024:
            raise ValueError("Upload a valid PDF under 50 MB.")
        document_hash = sha256(pdf_bytes).hexdigest()
        storage_key = f"{document_hash}.pdf"
        notice_id = str(uuid4())
        now = utc_now()
        metadata = analysis.metadata
        actual_title = (title or metadata.title or "").strip()
        if not actual_title or len(actual_title) > 300:
            raise ValueError("Enter the title shown in the notice.")
        deadlines = [
            {"date_type": item.date_type.value, "value": item.value, "time": item.time,
             "source_text": item.source_text, "evidence_ids": item.evidence_ids}
            for item in analysis.dates
            if item.date_type.value in {"application_deadline", "fee_payment_deadline", "correction_deadline"}
        ]
        path = self.storage_dir / storage_key
        created_blob = False
        try:
            with self.store._connect() as connection:
                self._require_admin(connection, account_id)
                duplicate = connection.execute(
                    "SELECT notice_id FROM notice_library WHERE document_sha256=?", (document_hash,)
                ).fetchone()
                if duplicate:
                    raise DuplicateNotice(duplicate["notice_id"])
                if not path.exists():
                    fd, temporary_name = tempfile.mkstemp(prefix=".notice-", suffix=".tmp", dir=self.storage_dir)
                    try:
                        with os.fdopen(fd, "wb") as stream:
                            stream.write(pdf_bytes)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary_name, path)
                        created_blob = True
                    finally:
                        if os.path.exists(temporary_name):
                            os.unlink(temporary_name)
                connection.execute(
                    "INSERT INTO notice_library(notice_id,document_sha256,storage_key,owner_id,title,issuing_authority,source_url,source_language,publication_date,deadlines_json,analysis_json,publication_state,eligibility_reviewed,uploaded_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,'draft',0,?,?)",
                    (notice_id, document_hash, storage_key, account_id, actual_title,
                     metadata.issuing_authority, metadata.source_url, analysis.source_language,
                     metadata.publication_date, json.dumps(deadlines, ensure_ascii=False),
                     analysis.model_dump_json(), now, now),
                )
        except Exception:
            if created_blob:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        return self.get_for_account(account_id, notice_id)

    def update_analysis(self, account_id: str, notice_id: str, analysis: NoticeAnalysis,
                        title: str | None = None) -> NoticeRecord:
        metadata = analysis.metadata
        actual_title = (title or metadata.title or "").strip()
        if not actual_title or len(actual_title) > 300:
            raise ValueError("Enter the title shown in the notice.")
        deadlines = [
            {"date_type": item.date_type.value, "value": item.value, "time": item.time,
             "source_text": item.source_text, "evidence_ids": item.evidence_ids}
            for item in analysis.dates
            if item.date_type.value in {"application_deadline", "fee_payment_deadline", "correction_deadline"}
        ]
        with self.store._connect() as connection:
            self._require_admin(connection, account_id)
            changed = connection.execute(
                "UPDATE notice_library SET title=?,issuing_authority=?,source_url=?,source_language=?,publication_date=?,deadlines_json=?,analysis_json=?,eligibility_reviewed=0,eligibility_reviewed_by=NULL,eligibility_reviewed_at=NULL,updated_at=? WHERE notice_id=?",
                (actual_title, metadata.issuing_authority, metadata.source_url, analysis.source_language,
                 metadata.publication_date, json.dumps(deadlines, ensure_ascii=False),
                 analysis.model_dump_json(), utc_now(), notice_id),
            ).rowcount
            if not changed:
                raise NoticeUnavailable("Notice not found.")
        from services.auth.notifications import NotificationService
        NotificationService(self.store).reconcile_notice(notice_id)
        return self.get_for_account(account_id, notice_id)

    def set_publication(self, account_id: str, notice_id: str, published: bool) -> None:
        with self.store._connect() as connection:
            self._require_admin(connection, account_id)
            row = connection.execute("SELECT analysis_json FROM notice_library WHERE notice_id=?", (notice_id,)).fetchone()
            if not row:
                raise NoticeUnavailable("Notice not found.")
            state = "published" if published else "draft"
            connection.execute(
                "UPDATE notice_library SET publication_state=?,published_at=?,updated_at=? WHERE notice_id=?",
                (state, utc_now() if published else None, utc_now(), notice_id),
            )
        from services.auth.notifications import NotificationService
        service = NotificationService(self.store)
        if published:
            service.notify_new_notice(notice_id)
        else:
            with self.store._connect() as connection:
                connection.execute("UPDATE notifications SET active=0 WHERE notice_id=?", (notice_id,))

    def set_eligibility_review(self, account_id: str, notice_id: str, reviewed: bool) -> None:
        """Persist an admin's explicit completeness attestation and audit identity."""
        with self.store._connect() as connection:
            self._require_admin(connection, account_id)
            row = connection.execute(
                "SELECT analysis_json FROM notice_library WHERE notice_id=?", (notice_id,)
            ).fetchone()
            if not row:
                raise NoticeUnavailable("Notice not found.")
            if reviewed:
                analysis = NoticeAnalysis.model_validate_json(row["analysis_json"])
                if not has_reviewable_eligibility_coverage(analysis):
                    raise ValueError("Review requires supported, source-cited eligibility conditions.")
                reviewed_by, reviewed_at = account_id, utc_now()
            else:
                reviewed_by, reviewed_at = None, None
            connection.execute(
                "UPDATE notice_library SET eligibility_reviewed=?,eligibility_reviewed_by=?,eligibility_reviewed_at=?,updated_at=? WHERE notice_id=?",
                (int(bool(reviewed)), reviewed_by, reviewed_at, utc_now(), notice_id),
            )
        from services.auth.notifications import NotificationService
        notifications = NotificationService(self.store)
        if reviewed:
            notifications.notify_new_notice(notice_id)
        notifications.reconcile_notice(notice_id)

    def remove(self, account_id: str, notice_id: str) -> None:
        storage_key = None
        with self.store._connect() as connection:
            self._require_admin(connection, account_id)
            row = connection.execute("SELECT storage_key FROM notice_library WHERE notice_id=?", (notice_id,)).fetchone()
            if not row:
                raise NoticeUnavailable("Notice not found.")
            storage_key = row["storage_key"]
            connection.execute("DELETE FROM notice_library WHERE notice_id=?", (notice_id,))
        if storage_key:
            (self.storage_dir / storage_key).unlink(missing_ok=True)

    def list_published(self, *, query: str = "", language: str = "", issuer: str = "",
                       deadline_before: str = "") -> list[NoticeRecord]:
        clauses = ["publication_state='published'"]
        params: list[object] = []
        if query.strip():
            term = _like_term(query.strip())
            clauses.append("(title LIKE ? ESCAPE '\\' OR issuing_authority LIKE ? ESCAPE '\\')")
            params.extend((term, term))
        if language in {"en", "te", "hi", "mixed"}:
            clauses.append("source_language=?")
            params.append(language)
        if issuer.strip():
            clauses.append("issuing_authority LIKE ? ESCAPE '\\'")
            params.append(_like_term(issuer.strip()))
        rows = self._rows(" AND ".join(clauses), params)
        result = [_row_record(row) for row in rows]
        if deadline_before:
            try:
                cutoff = date.fromisoformat(deadline_before)
            except ValueError:
                return []
            result = [notice for notice in result if any(
                item.get("value") and date.fromisoformat(item["value"]) <= cutoff
                for item in notice.deadlines
            )]
        return result

    def list_admin(self, account_id: str) -> list[NoticeRecord]:
        with self.store._connect() as connection:
            self._require_admin(connection, account_id)
            rows = connection.execute("SELECT * FROM notice_library ORDER BY uploaded_at DESC").fetchall()
        return [_row_record(row) for row in rows]

    def get_for_account(self, account_id: str, notice_id: str) -> NoticeRecord:
        with self.store._connect() as connection:
            is_admin = connection.execute("SELECT is_admin FROM accounts WHERE account_id=?", (account_id,)).fetchone()
            row = connection.execute(
                "SELECT * FROM notice_library WHERE notice_id=? AND (publication_state='published' OR owner_id=? OR ?=1)",
                (notice_id, account_id, int(bool(is_admin and is_admin["is_admin"]))),
            ).fetchone()
        if not row:
            raise NoticeUnavailable("Notice not found.")
        return _row_record(row)

    def get_pdf_for_account(self, account_id: str, notice_id: str) -> bytes:
        notice = self.get_for_account(account_id, notice_id)
        path = self.storage_dir / notice.storage_key
        if not path.is_file():
            raise NoticeUnavailable("The notice document is unavailable.")
        contents = path.read_bytes()
        if sha256(contents).hexdigest() != notice.document_sha256:
            raise NoticeUnavailable("The notice document did not pass its integrity check.")
        return contents

    def _rows(self, where: str, params: Iterable[object]) -> list[sqlite3.Row]:
        with self.store._connect() as connection:
            return connection.execute(
                f"SELECT * FROM notice_library WHERE {where} ORDER BY published_at DESC, title COLLATE NOCASE",
                tuple(params),
            ).fetchall()


def database_path_parent(database_path: str) -> Path:
    if database_path == ":memory:":
        raise ValueError("The notice library requires a persistent SQLite database.")
    return Path(database_path).resolve().parent


def _like_term(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"

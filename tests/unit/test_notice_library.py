"""Notice-library storage permissions and state transitions."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from indicnotice.schemas.notice import NoticeAnalysis, NoticeMetadata
from demo.product import initial_analysis
from services.auth.notices import DuplicateNotice, NoticeLibrary, NoticeUnavailable
from services.auth.store import AuthStore, AuthorizationError


PASSWORD = "Local Notice Admin Pass 998!"


def _analysis(title: str = "Library Test Notice") -> NoticeAnalysis:
    return NoticeAnalysis(
        analysis_id="analysis-test", document_id="document-test",
        metadata=NoticeMetadata(title=title),
    )


def _account(store: AuthStore, email: str):
    return store.register(email, PASSWORD)


def test_admin_only_upload_private_drafts_publication_and_pdf_access(tmp_path: Path):
    database = tmp_path / "accounts.sqlite3"
    store = AuthStore(database)
    admin = _account(store, "operator@example.test")
    student_a = _account(store, "a@example.test")
    student_b = _account(store, "b@example.test")
    library = NoticeLibrary(store)
    pdf = b"%PDF-1.7\ncontrolled storage test\n%%EOF"

    with pytest.raises(AuthorizationError):
        library.create_draft(student_a["account_id"], pdf, _analysis())
    store.grant_admin(admin["email"], PASSWORD)
    assert store.is_admin(admin["account_id"])

    draft = library.create_draft(admin["account_id"], pdf, _analysis())
    assert draft.publication_state == "draft"
    assert library.list_published() == []
    with pytest.raises(NoticeUnavailable):
        library.get_for_account(student_a["account_id"], draft.notice_id)
    with pytest.raises(NoticeUnavailable):
        library.get_pdf_for_account(student_a["account_id"], draft.notice_id)
    assert library.get_pdf_for_account(admin["account_id"], draft.notice_id) == pdf
    with pytest.raises(DuplicateNotice):
        library.create_draft(admin["account_id"], pdf, _analysis())

    library.set_publication(admin["account_id"], draft.notice_id, True)
    assert [item.title for item in library.list_published(query="Library Test")] == ["Library Test Notice"]
    assert library.get_pdf_for_account(student_a["account_id"], draft.notice_id) == pdf
    assert library.get_for_account(student_b["account_id"], draft.notice_id).notice_id == draft.notice_id

    library.set_publication(admin["account_id"], draft.notice_id, False)
    assert library.list_published() == []
    with pytest.raises(NoticeUnavailable):
        library.get_for_account(student_a["account_id"], draft.notice_id)

    library.remove(admin["account_id"], draft.notice_id)
    assert not library.list_admin(admin["account_id"])
    with pytest.raises(AuthorizationError):
        library.list_admin(student_a["account_id"])
    with pytest.raises(AuthorizationError):
        library.set_publication(student_b["account_id"], draft.notice_id, True)


def test_notice_records_persist_and_reanalysis_clears_review_across_restart(tmp_path: Path):
    database = tmp_path / "accounts.sqlite3"
    store = AuthStore(database)
    admin = _account(store, "operator@example.test")
    store.grant_admin(admin["email"], PASSWORD)
    library = NoticeLibrary(store)
    pdf_path = Path("datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf")
    pdf = pdf_path.read_bytes()
    analysis = initial_analysis(pdf, pdf_path.name).analysis
    draft = library.create_draft(admin["account_id"], pdf, analysis)
    library.set_eligibility_review(admin["account_id"], draft.notice_id, True)
    library.set_publication(admin["account_id"], draft.notice_id, True)
    reviewed = library.get_for_account(admin["account_id"], draft.notice_id)
    assert reviewed.eligibility_reviewed
    assert reviewed.eligibility_reviewed_by == admin["account_id"]
    assert reviewed.eligibility_reviewed_at

    restarted_store = AuthStore(database)
    restarted = NoticeLibrary(restarted_store)
    visible = restarted.get_for_account(admin["account_id"], draft.notice_id)
    assert visible.title == draft.title
    assert visible.eligibility_reviewed
    assert visible.eligibility_reviewed_by == admin["account_id"]
    assert visible.eligibility_reviewed_at == reviewed.eligibility_reviewed_at
    assert restarted.get_pdf_for_account(admin["account_id"], draft.notice_id) == pdf
    restarted.update_analysis(admin["account_id"], draft.notice_id, _analysis("Updated title"))
    updated = restarted.get_for_account(admin["account_id"], draft.notice_id)
    assert updated.publication_state == "published"
    assert updated.title == "Updated title"
    assert not updated.eligibility_reviewed
    assert updated.eligibility_reviewed_by is None
    assert updated.eligibility_reviewed_at is None

    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall() == [(1,), (2,), (3,), (4,)]
        assert connection.execute("SELECT count(*) FROM notice_library").fetchone()[0] == 1


def test_version_two_migration_upgrades_existing_version_one_database(tmp_path: Path):
    database = tmp_path / "legacy.sqlite3"
    migration = (Path("services/auth/migrations/001_initial.sql")).read_text(encoding="utf-8")
    with sqlite3.connect(database) as connection:
        connection.executescript(migration)
        connection.execute("INSERT INTO schema_migrations(version,applied_at) VALUES(1,'test')")
    store = AuthStore(database)
    with sqlite3.connect(database) as connection:
        versions = connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
        assert versions == [(1,), (2,), (3,), (4,)]
        assert "is_admin" in columns
        assert store.database_path == str(database.resolve())

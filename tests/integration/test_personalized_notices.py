"""Personalized matching against the checked-in, real notice PDFs."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from demo.product import initial_analysis
from demo.notices_ui import _condition_explanations, _details
from services.auth.notices import NoticeLibrary, evaluate_notice
from services.auth.store import AuthStore, AuthorizationError
import pytest


ROOT = Path(__file__).resolve().parents[2]
HINDI_SCERT = ROOT / "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf"
TELUGU_KVS = ROOT / "datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf"
PASSWORD = "Acceptance Admin Passphrase 387!"


def test_real_hindi_qualifying_failing_and_incomplete_profiles_are_cited(tmp_path: Path):
    store = AuthStore(tmp_path / "accounts.sqlite3")
    admin = store.register("admin@example.test", PASSWORD)
    student = store.register("student@example.test", PASSWORD)
    store.grant_admin(admin["email"], PASSWORD)
    library = NoticeLibrary(store)

    analysis = initial_analysis(HINDI_SCERT.read_bytes(), HINDI_SCERT.name)
    notice = library.create_draft(admin["account_id"], HINDI_SCERT.read_bytes(), analysis.analysis)
    assert not notice.eligibility_reviewed
    unreviewed = evaluate_notice(notice, {
        "marks_percentage": 80, "current_class": 8, "previous_class": 7,
        "current_school_type": "government", "previous_school_type": "government",
        "annual_family_income_inr": 200000, "attempt_count": 1,
    })
    assert unreviewed.status == "requirements_met_so_far"
    assert not unreviewed.coverage_complete
    library.set_eligibility_review(admin["account_id"], notice.notice_id, True)
    reviewed_record = library.get_for_account(admin["account_id"], notice.notice_id)
    assert reviewed_record.eligibility_reviewed_by == admin["account_id"]
    assert reviewed_record.eligibility_reviewed_at
    with pytest.raises(AuthorizationError):
        library.set_eligibility_review(student["account_id"], notice.notice_id, False)
    library.set_publication(admin["account_id"], notice.notice_id, True)
    published = library.get_for_account(student["account_id"], notice.notice_id)
    assert published.eligibility_reviewed
    assert published.eligibility_reviewed_at == reviewed_record.eligibility_reviewed_at
    assert published.analysis.source_language == "hi"
    assert published.deadlines[0]["value"] == "2025-10-15"

    qualifies = {
        "marks_percentage": 80,
        "current_class": 8,
        "previous_class": 7,
        "current_school_type": "government",
        "previous_school_type": "government",
        "annual_family_income_inr": 200000,
        "attempt_count": 1,
    }
    qualifying = evaluate_notice(published, qualifies)
    failing = evaluate_notice(published, {**qualifies, "marks_percentage": 50})
    incomplete = evaluate_notice(published, {"current_class": 8})

    assert qualifying.status == "reviewed_requirements_met"
    assert qualifying.coverage_complete
    assert all(item.source_pages for item in qualifying.explanation.conditions)
    # Exercise the same evidence-rendering helper used by the live Streamlit
    # For You and details pages. This catches runtime import/name errors.
    ui = Mock()
    _condition_explanations(ui, qualifying, "en")
    assert ui.write.call_count >= len(qualifying.explanation.conditions)
    assert ui.caption.call_count > 0
    detail_ui = Mock()
    detail_ui.session_state = {"selected_library_notice": notice.notice_id}
    _details(detail_ui, library, {"account_id": student["account_id"]}, qualifies, "en")
    assert detail_ui.download_button.call_count == 1
    assert detail_ui.subheader.call_count >= 1
    assert failing.status == "does_not_meet"
    assert failing.explanation.overall.value == "FAIL"
    assert incomplete.status == "needs_information"
    assert incomplete.explanation.overall.value == "UNKNOWN"

    # Matching has no cached profile key: a profile update changes the next result.
    updated_profile_result = evaluate_notice(published, {**qualifies, "marks_percentage": 54})
    assert updated_profile_result.status == "does_not_meet"
    library.set_eligibility_review(admin["account_id"], notice.notice_id, False)
    reversed_notice = library.get_for_account(student["account_id"], notice.notice_id)
    assert evaluate_notice(reversed_notice, qualifies).status == "requirements_met_so_far"


def test_real_telugu_kvs_notice_is_published_discoverable_and_unknown(tmp_path: Path):
    store = AuthStore(tmp_path / "accounts.sqlite3")
    admin = store.register("admin@example.test", PASSWORD)
    student = store.register("student@example.test", PASSWORD)
    store.grant_admin(admin["email"], PASSWORD)
    library = NoticeLibrary(store)

    analysis = initial_analysis(TELUGU_KVS.read_bytes(), TELUGU_KVS.name)
    notice = library.create_draft(admin["account_id"], TELUGU_KVS.read_bytes(), analysis.analysis)
    assert notice.analysis.eligibility is None
    library.set_publication(admin["account_id"], notice.notice_id, True)
    public_results = library.list_published(query="Kendriya")
    assert [item.notice_id for item in public_results] == [notice.notice_id]
    assert evaluate_notice(public_results[0], {"current_class": 1}).status == "needs_information"
    assert library.get_pdf_for_account(student["account_id"], notice.notice_id).startswith(b"%PDF-")

    library.set_publication(admin["account_id"], notice.notice_id, False)
    assert library.list_published(query="Kendriya") == []

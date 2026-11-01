from __future__ import annotations

from datetime import date
from pathlib import Path

from demo.product import initial_analysis
from services.auth.notices import NoticeLibrary
from services.auth.notifications import NotificationService
from services.auth.store import AuthStore

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf"
PASSWORD = "Acceptance Admin Passphrase 387!"
PROFILE = {
    "marks_percentage": 80, "current_class": 8, "previous_class": 7,
    "current_school_type": "government", "previous_school_type": "government",
    "annual_family_income_inr": 200000, "attempt_count": 1,
}


def test_notification_publication_is_scoped_idempotent_and_reconciled(tmp_path):
    store = AuthStore(tmp_path / "notifications.sqlite3")
    admin = store.register("admin@example.test", PASSWORD)
    qualifying = store.register("qualifying@example.test", PASSWORD)
    failing = store.register("failing@example.test", PASSWORD)
    incomplete = store.register("incomplete@example.test", PASSWORD)
    store.grant_admin(admin["email"], PASSWORD)
    store.replace_profile(qualifying["account_id"], PROFILE)
    store.replace_profile(failing["account_id"], {**PROFILE, "marks_percentage": 50})
    service = NotificationService(store)
    service.save_preferences(incomplete["account_id"], {"more_information": True})
    library = NoticeLibrary(store)
    pdf = FIXTURE.read_bytes()
    analysis = initial_analysis(pdf, FIXTURE.name).analysis
    notice = library.create_draft(admin["account_id"], pdf, analysis)
    library.set_eligibility_review(admin["account_id"], notice.notice_id, True)
    library.set_publication(admin["account_id"], notice.notice_id, True)
    library.set_publication(admin["account_id"], notice.notice_id, True)

    assert [n["event_type"] for n in service.list_for_user(qualifying["account_id"])] == ["relevant_notice"]
    assert service.list_for_user(failing["account_id"]) == []
    assert [n["event_type"] for n in service.list_for_user(incomplete["account_id"])] == ["more_information"]
    assert service.unread_count(qualifying["account_id"]) == 1
    # A profile transition to failing withdraws an active event; the profile is
    # never copied into the notification record.
    store.replace_profile(qualifying["account_id"], {**PROFILE, "marks_percentage": 50})
    assert service.list_for_user(qualifying["account_id"]) == []
    assert service.list_for_user(failing["account_id"]) == []

    # The real Hindi PDF has an expired 2025 date; no fictional reminders.
    assert service.generate_due_reminders(as_of=date(2026, 10, 28)) == 0
    library.set_publication(admin["account_id"], notice.notice_id, False)
    assert service.list_for_user(incomplete["account_id"]) == []


def test_notification_mark_read_and_account_deletion_are_scoped(tmp_path):
    store = AuthStore(tmp_path / "notifications.sqlite3")
    admin = store.register("admin@example.test", PASSWORD)
    student = store.register("student@example.test", PASSWORD)
    other = store.register("other@example.test", PASSWORD)
    store.grant_admin(admin["email"], PASSWORD)
    service = NotificationService(store)
    library = NoticeLibrary(store)
    pdf = FIXTURE.read_bytes()
    notice = library.create_draft(admin["account_id"], pdf, initial_analysis(pdf, FIXTURE.name).analysis)
    library.set_eligibility_review(admin["account_id"], notice.notice_id, True)
    store.replace_profile(student["account_id"], PROFILE)
    library.set_publication(admin["account_id"], notice.notice_id, True)
    own = service.list_for_user(student["account_id"])
    assert own
    service.mark_read(other["account_id"], own[0]["notification_id"])
    assert service.list_for_user(student["account_id"])[0]["read_at"] is None
    service.mark_read(student["account_id"], own[0]["notification_id"])
    assert service.list_for_user(student["account_id"])[0]["read_at"] is not None
    store.delete_account(student["account_id"], PASSWORD)
    with store._connect() as db:
        assert db.execute("SELECT count(*) FROM notifications WHERE user_id=?", (student["account_id"],)).fetchone()[0] == 0


def test_deadline_reminders_use_controlled_date_and_are_idempotent(tmp_path):
    store = AuthStore(tmp_path / "reminders.sqlite3")
    admin = store.register("admin@example.test", PASSWORD)
    student = store.register("student@example.test", PASSWORD)
    store.grant_admin(admin["email"], PASSWORD)
    store.replace_profile(student["account_id"], PROFILE)
    raw = FIXTURE.read_bytes()
    analysis = initial_analysis(raw, FIXTURE.name).analysis
    deadline = next(item for item in analysis.dates if item.date_type.value == "application_deadline")
    changed_deadline = deadline.model_copy(update={"value": "2026-11-04"})
    changed_dates = [changed_deadline if item is deadline else item for item in analysis.dates]
    reminder_analysis = analysis.model_copy(update={"dates": changed_dates})
    library = NoticeLibrary(store)
    notice = library.create_draft(admin["account_id"], raw, reminder_analysis)
    library.set_eligibility_review(admin["account_id"], notice.notice_id, True)
    library.set_publication(admin["account_id"], notice.notice_id, True)
    service = NotificationService(store)
    assert service.generate_due_reminders(as_of=date(2026, 10, 28)) == 1
    assert service.generate_due_reminders(as_of=date(2026, 10, 28)) == 0
    entry = next(item for item in service.list_for_user(student["account_id"]) if item["event_type"] == "deadline")
    assert (entry["event_type"], entry["reminder_days"]) == ("deadline", 7)
    service.mark_read(student["account_id"], entry["notification_id"])

    # Reanalysis changes the deadline; prior reminder events are removed.
    later_deadline = changed_deadline.model_copy(update={"value": "2026-11-05"})
    changed_again = analysis.model_copy(update={
        "dates": [later_deadline if item is deadline else item for item in analysis.dates]
    })
    library.update_analysis(admin["account_id"], notice.notice_id, changed_again)
    assert service.list_for_user(student["account_id"]) == []

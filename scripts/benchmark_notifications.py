"""Measure isolated notification fan-out, reminder generation and reads."""
from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.product import initial_analysis
from services.auth.notices import NoticeLibrary
from services.auth.notifications import NotificationService
from services.auth.store import AuthStore

FIXTURE = ROOT / "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf"
PASSWORD = "Notifications benchmark-only passphrase 486!"
PROFILE = {"marks_percentage": 80, "current_class": 8, "previous_class": 7,
           "current_school_type": "government", "previous_school_type": "government",
           "annual_family_income_inr": 200000, "attempt_count": 1}


def samples(fn, count=100):
    timings = []
    for _ in range(count):
        start = time.perf_counter()
        fn()
        timings.append(time.perf_counter() - start)
    return {"iterations": count, "total_seconds": round(sum(timings), 6),
            "mean_seconds": round(statistics.mean(timings), 6),
            "p95_seconds": round(sorted(timings)[int(.95 * (count - 1))], 6)}


def main():
    raw = FIXTURE.read_bytes()
    analysis = initial_analysis(raw, FIXTURE.name).analysis
    with tempfile.TemporaryDirectory(prefix="indicnotice-v2c-notifications-") as temporary:
        store = AuthStore(Path(temporary) / "isolated.sqlite3")
        admin = store.register("admin@example.test", PASSWORD)
        store.grant_admin(admin["email"], PASSWORD)
        users = [store.register(f"student-{n}@example.test", PASSWORD) for n in range(20)]
        for user in users:
            store.replace_profile(user["account_id"], PROFILE)
        library = NoticeLibrary(store)
        service = NotificationService(store)
        notice = library.create_draft(admin["account_id"], raw, analysis)
        library.set_eligibility_review(admin["account_id"], notice.notice_id, True)
        start = time.perf_counter()
        library.set_publication(admin["account_id"], notice.notice_id, True)
        fanout = time.perf_counter() - start
        with store._connect() as db:
            fanout_created = db.execute("SELECT count(*) FROM notifications WHERE notice_id=?", (notice.notice_id,)).fetchone()[0]
        notification_reads = samples(lambda: service.list_for_user(users[0]["account_id"]))
        time_now = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        reminder_date = time_now + timedelta(days=7)
        deadline = next(item for item in analysis.dates if item.date_type.value == "application_deadline")
        changed = deadline.model_copy(update={"value": reminder_date.isoformat()})
        reminder_analysis = analysis.model_copy(update={
            "dates": [changed if item is deadline else item for item in analysis.dates]
        })
        # Isolated QA-only copy of the checked-in PDF analysis; the production
        # notice and historical source PDF remain untouched.
        qa_pdf = raw + b"\n% isolated reminder timing fixture\n"
        reminder_notice = library.create_draft(admin["account_id"], qa_pdf, reminder_analysis)
        library.set_eligibility_review(admin["account_id"], reminder_notice.notice_id, True)
        library.set_publication(admin["account_id"], reminder_notice.notice_id, True)
        start = time.perf_counter()
        reminder_rows = service.generate_due_reminders(as_of=time_now)
        reminder_seconds = time.perf_counter() - start
        output = {
            "fixture": FIXTURE.relative_to(ROOT).as_posix(),
            "isolated_accounts": len(users),
            "notification_fanout": {"users": len(users), "created": fanout_created,
                                    "seconds": round(fanout, 6), "includes_publish_and_match": True},
            "notifications_page_read": notification_reads,
            "deadline_reminder_generation": {"users": len(users), "created": reminder_rows,
                                             "seconds": round(reminder_seconds, 6),
                                             "controlled_deadline": reminder_date.isoformat()},
            "data_policy": "Temporary SQLite database; real SCERT analysis. Future deadline override is isolated test data only.",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

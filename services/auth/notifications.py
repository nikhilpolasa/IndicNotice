"""Persistent, account-scoped in-app notice events and daily deadline reminders."""
from __future__ import annotations

from datetime import date, datetime, timezone
import argparse
import sqlite3
from uuid import uuid4

from services.auth.notices import NoticeLibrary, evaluate_notice
from services.auth.store import AuthStore, AuthorizationError, utc_now

PREFERENCE_DEFAULTS = {
    "relevant_notices": True, "more_information": False,
    "reminder_7_days": True, "reminder_3_days": True, "reminder_1_day": True,
}


class NotificationService:
    def __init__(self, store: AuthStore):
        self.store = store
        self.library = NoticeLibrary(store)

    def _account(self, account_id: str) -> None:
        with self.store._connect() as db:
            if not db.execute("SELECT 1 FROM accounts WHERE account_id=?", (account_id,)).fetchone():
                raise AuthorizationError("Sign in is required.")

    def preferences(self, account_id: str) -> dict[str, bool]:
        self._account(account_id)
        with self.store._connect() as db:
            row = db.execute("SELECT * FROM notification_preferences WHERE account_id=?", (account_id,)).fetchone()
        return dict(PREFERENCE_DEFAULTS) if row is None else {k: bool(row[k]) for k in PREFERENCE_DEFAULTS}

    def save_preferences(self, account_id: str, values: dict[str, bool]) -> None:
        self._account(account_id)
        clean = {key: bool(values.get(key, PREFERENCE_DEFAULTS[key])) for key in PREFERENCE_DEFAULTS}
        now = utc_now()
        with self.store._connect() as db:
            db.execute("INSERT INTO notification_preferences(account_id,updated_at) VALUES(?,?) ON CONFLICT(account_id) DO NOTHING", (account_id, now))
            db.execute("UPDATE notification_preferences SET relevant_notices=?,more_information=?,reminder_7_days=?,reminder_3_days=?,reminder_1_day=?,updated_at=? WHERE account_id=?",
                       (*[int(clean[k]) for k in PREFERENCE_DEFAULTS], now, account_id))
        self.reconcile_user(account_id)

    def _prefs(self, db: sqlite3.Connection, account_id: str) -> dict[str, bool]:
        row = db.execute("SELECT * FROM notification_preferences WHERE account_id=?", (account_id,)).fetchone()
        return dict(PREFERENCE_DEFAULTS) if row is None else {k: bool(row[k]) for k in PREFERENCE_DEFAULTS}

    def unread_count(self, account_id: str) -> int:
        self._account(account_id)
        with self.store._connect() as db:
            return int(db.execute("SELECT count(*) FROM notifications n JOIN notice_library l USING(notice_id) WHERE n.user_id=? AND n.active=1 AND n.read_at IS NULL AND l.publication_state='published'", (account_id,)).fetchone()[0])

    def list_for_user(self, account_id: str) -> list[dict]:
        self._account(account_id)
        with self.store._connect() as db:
            rows = db.execute("SELECT n.notification_id,n.notice_id,n.event_type,n.reminder_days,n.created_at,n.read_at,l.title,l.deadlines_json FROM notifications n JOIN notice_library l USING(notice_id) WHERE n.user_id=? AND n.active=1 AND l.publication_state='published' ORDER BY n.created_at DESC", (account_id,)).fetchall()
        return [dict(row) for row in rows]

    def mark_read(self, account_id: str, notification_id: str) -> None:
        self._account(account_id)
        with self.store._connect() as db:
            db.execute("UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE notification_id=? AND user_id=? AND active=1",
                       (utc_now(), notification_id, account_id))

    def mark_all_read(self, account_id: str) -> None:
        self._account(account_id)
        with self.store._connect() as db:
            db.execute("UPDATE notifications SET read_at=COALESCE(read_at,?) WHERE user_id=? AND active=1", (utc_now(), account_id))

    def reconcile_user(self, account_id: str) -> None:
        """Re-evaluate only the signed-in account after profile/preference updates."""
        self._account(account_id)
        profile = self.store.get_profile(account_id)
        preferences = self.preferences(account_id)
        notices = self.library.list_published()
        desired: set[tuple[str, str, int]] = set()
        for notice in notices:
            match = evaluate_notice(notice, profile)
            if match.status == "reviewed_requirements_met" and preferences["relevant_notices"]:
                desired.add((notice.notice_id, "relevant_notice", 0))
            elif match.status in {"requirements_met_so_far", "needs_information"} and preferences["more_information"]:
                desired.add((notice.notice_id, "more_information", 0))
        now = utc_now()
        with self.store._connect() as db:
            db.execute("UPDATE notifications SET active=0 WHERE user_id=? AND event_type IN ('relevant_notice','more_information')", (account_id,))
            # Profile edits may revoke or restore a previously issued event, but
            # must not manufacture a "new notice" notification for old notices.
            for notice_id, event_type, days in desired:
                db.execute("UPDATE notifications SET active=1 WHERE user_id=? AND notice_id=? AND event_type=? AND reminder_days=?",
                           (account_id, notice_id, event_type, days))

    def notify_new_notice(self, notice_id: str) -> None:
        notice = next((n for n in self.library.list_published() if n.notice_id == notice_id), None)
        if notice is None:
            return
        with self.store._connect() as db:
            accounts = [row[0] for row in db.execute("SELECT account_id FROM accounts").fetchall()]
        now = utc_now()
        for account_id in accounts:
            profile = self.store.get_profile(account_id)
            match = evaluate_notice(notice, profile)
            if match.status == "does_not_meet":
                continue
            with self.store._connect() as db:
                prefs = self._prefs(db, account_id)
                if match.status == "reviewed_requirements_met" and prefs["relevant_notices"]:
                    event = "relevant_notice"
                elif match.status in {"requirements_met_so_far", "needs_information"} and prefs["more_information"]:
                    event = "more_information"
                else:
                    continue
                db.execute("INSERT OR IGNORE INTO notifications(notification_id,user_id,notice_id,event_type,reminder_days,created_at,active) VALUES(?,?,?,?,0,?,1)",
                           (str(uuid4()), account_id, notice_id, event, now))

    def reconcile_notice(self, notice_id: str) -> None:
        with self.store._connect() as db:
            accounts = [row[0] for row in db.execute("SELECT account_id FROM accounts").fetchall()]
        for account_id in accounts:
            self.reconcile_user(account_id)
        with self.store._connect() as db:
            db.execute("DELETE FROM notifications WHERE notice_id=? AND event_type='deadline'", (notice_id,))

    def generate_due_reminders(self, *, as_of: date | None = None, timezone_name: str = "Asia/Kolkata") -> int:
        """Create idempotent reminders for windows exactly 7/3/1 days before due dates."""
        from zoneinfo import ZoneInfo
        local_today = as_of or datetime.now(ZoneInfo(timezone_name)).date()
        notices = self.library.list_published()
        made = 0
        with self.store._connect() as db:
            accounts = [row[0] for row in db.execute("SELECT account_id FROM accounts").fetchall()]
        for notice in notices:
            dates = {date.fromisoformat(item["value"]) for item in notice.deadlines
                     if item.get("date_type") == "application_deadline" and item.get("value") and item.get("evidence_ids")}
            for deadline in dates:
                days = (deadline - local_today).days
                if days not in (7, 3, 1):
                    continue
                for account_id in accounts:
                    profile = self.store.get_profile(account_id)
                    match = evaluate_notice(notice, profile)
                    if match.status == "does_not_meet":
                        continue
                    with self.store._connect() as db:
                        pref = self._prefs(db, account_id)
                        if match.status != "reviewed_requirements_met" and not pref["more_information"]:
                            continue
                        preference_key = "reminder_7_days" if days == 7 else "reminder_3_days" if days == 3 else "reminder_1_day"
                        if not pref[preference_key]:
                            continue
                        cursor = db.execute("INSERT OR IGNORE INTO notifications(notification_id,user_id,notice_id,event_type,reminder_days,created_at,active) VALUES(?,?,?,?,?,?,1)",
                                            (str(uuid4()), account_id, notice.notice_id, "deadline", days, utc_now()))
                        made += cursor.rowcount
        return made


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate idempotent IndicNotice deadline reminders.")
    parser.add_argument("--timezone", default="Asia/Kolkata")
    parser.add_argument("--as-of", help="Controlled date for isolated QA only (YYYY-MM-DD).")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    created = NotificationService(AuthStore()).generate_due_reminders(as_of=as_of, timezone_name=args.timezone)
    print(f"Created {created} deadline reminder(s).")


if __name__ == "__main__":
    main()

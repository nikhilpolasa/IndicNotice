"""Measure authenticated notification-page rendering in an isolated audit app."""
from __future__ import annotations

import json
import os
from pathlib import Path
import statistics
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from browser_notifications import select_section, set_language
from browser_personalized_notices import CDP, login, page_for
from services.auth.notices import NoticeLibrary
from services.auth.notifications import NotificationService
from services.auth.store import AuthStore

DB = os.environ["INDICNOTICE_AUTH_DB"]
BASE = os.environ.get("INDICNOTICE_AUDIT_ORIGIN", "http://127.0.0.1:8501")
PORT = int(os.environ.get("INDICNOTICE_CDP_PORT", "9222"))
PASSWORD = os.environ["INDICNOTICE_AUDIT_PASSWORD"]
EMAIL = os.environ["INDICNOTICE_BENCH_STUDENT"]
ADMIN_EMAIL = os.environ["INDICNOTICE_BENCH_ADMIN"]


def main():
    store = AuthStore(DB)
    with store._connect() as db:
        student = db.execute("SELECT account_id FROM accounts WHERE email_normalized=?", (EMAIL.casefold(),)).fetchone()
        admin = db.execute("SELECT account_id FROM accounts WHERE email_normalized=?", (ADMIN_EMAIL.casefold(),)).fetchone()
        notice = db.execute("SELECT notice_id FROM notice_library ORDER BY uploaded_at DESC LIMIT 1").fetchone()
    if not student or not admin or not notice:
        raise RuntimeError("Isolated browser account or real notice is missing.")
    library = NoticeLibrary(store)
    library.set_publication(admin[0], notice[0], True)
    browser = CDP(json.load(urlopen(f"http://127.0.0.1:{PORT}/json/version"))["webSocketDebuggerUrl"])
    context = browser.call("Target.createBrowserContext")["browserContextId"]
    page = page_for(browser, context)
    try:
        login(page, EMAIL, PASSWORD)
        load_samples = []
        for _ in range(5):
            start = time.perf_counter()
            page.navigate(BASE + "/")
            page.wait("document.querySelectorAll('input[type=radio]').length>=4")
            load_samples.append(time.perf_counter() - start)
        set_language(page, "English", "Read a notice")
        start = time.perf_counter()
        select_section(page, "Notifications")
        page.wait("document.body.innerText.includes('You have no notifications yet.')")
        render_seconds = time.perf_counter() - start
        result = {
            "browser": "Chrome CDP, authenticated isolated user session",
            "notification_count": len(NotificationService(store).list_for_user(student[0])),
            "warm_app_navigation": {"samples_seconds": [round(x, 6) for x in load_samples], "mean_seconds": round(statistics.mean(load_samples), 6)},
            "notifications_page_render_empty_state_seconds": round(render_seconds, 6),
            "note": "This isolated user's page was empty; populated notification rendering is verified in the separate browser acceptance flow.",
        }
        (ROOT / "reports" / "notifications_ui_benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        library.set_publication(admin[0], notice[0], False)
        try:
            page.ws.close()
        except Exception:
            pass
        try:
            browser.call("Target.disposeBrowserContext", {"browserContextId": context})
        except Exception:
            pass
        browser.ws.close()


if __name__ == "__main__":
    main()

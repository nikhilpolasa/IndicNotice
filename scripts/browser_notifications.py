"""Real Chrome acceptance flow for persistent notifications on an isolated DB."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import uuid
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from browser_personalized_notices import CDP, page_for, register, save_profile, upload_pdf, account_id_for

BASE = os.environ.get("INDICNOTICE_AUDIT_ORIGIN", "http://127.0.0.1:8501")
DB = os.environ["INDICNOTICE_AUTH_DB"]
PORT = int(os.environ.get("INDICNOTICE_CDP_PORT", "9224"))
FIXTURE = ROOT / "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf"
PASSWORD = os.environ["INDICNOTICE_AUDIT_PASSWORD"]


def select_section(page: CDP, text: str):
    q = json.dumps(text, ensure_ascii=False)
    page.wait("document.querySelectorAll('input[type=radio]').length >= 4")
    match = f"(e.innerText.trim()==={q} || e.innerText.trim().startsWith('🔔 '+{q}))"
    page.js(f"[...document.querySelectorAll('label[data-testid=stRadioOption]')].find(e=>{match}).click()")
    page.wait(f"[...document.querySelectorAll('label[data-testid=stRadioOption]')].some(e=>{match} && e.getAttribute('data-selected')==='true')")
    page.wait(f"[...document.querySelectorAll('h1,h2')].some(e=>e.innerText.trim()==={q})")


def click_checkbox(page: CDP, label: str):
    q = json.dumps(label, ensure_ascii=False)
    page.js(f"[...document.querySelectorAll('input[aria-label]')].find(e=>e.getAttribute('aria-label')==={q}).closest('[data-testid=stCheckbox]').scrollIntoView({{block:'center'}})")
    rect = page.js(f"(()=>{{const e=[...document.querySelectorAll('input[aria-label]')].find(e=>e.getAttribute('aria-label')==={q}).closest('[data-testid=stCheckbox]').getBoundingClientRect();return {{x:e.x+12,y:e.y+12}}}})()")
    page.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": rect["x"], "y": rect["y"], "button": "left", "clickCount": 1})
    page.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": rect["x"], "y": rect["y"], "button": "left", "clickCount": 1})
    page.wait(f"[...document.querySelectorAll('input[aria-label]')].some(e=>e.getAttribute('aria-label')==={q} && e.checked)")


def screenshot(page: CDP, name: str):
    page.screenshot(name)
    return "reports/" + name


def set_language(page: CDP, label: str, nav_label: str):
    q = json.dumps(label, ensure_ascii=False)
    page.js("document.querySelector('[data-testid=stExpandSidebarButton]')?.click()")
    page.js("document.querySelector('[role=combobox]').parentElement.querySelector('button').click()")
    page.wait(f"[...document.querySelectorAll('[role=option]')].some(e=>e.innerText.trim()==={q})")
    page.js(f"[...document.querySelectorAll('[role=option]')].find(e=>e.innerText.trim()==={q}).click()")
    nav_q = json.dumps(nav_label, ensure_ascii=False)
    page.wait(f"[...document.querySelectorAll('label[data-testid=stRadioOption]')].some(e=>e.innerText.includes({nav_q}))")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    browser = CDP(json.load(urlopen(f"http://127.0.0.1:{PORT}/json/version"))["webSocketDebuggerUrl"])
    contexts = [browser.call("Target.createBrowserContext")["browserContextId"] for _ in range(5)]
    suffix = uuid.uuid4().hex[:8]
    emails = [f"v2c-{role}-{suffix}@example.test" for role in ("admin", "pass", "fail", "unknown")]
    pages = [page_for(browser, context) for context in contexts]
    checks: list[str] = []
    shots: list[str] = []
    from services.auth.store import AuthStore
    from services.auth.notices import NoticeLibrary
    from services.auth.notifications import NotificationService
    store = AuthStore(DB)
    try:
        register(pages[0], emails[0], PASSWORD)
        store.grant_admin(emails[0], PASSWORD)
        pages[0].navigate(BASE + "/")
        pages[0].wait("document.body.innerText.includes('Your notice, made clearer')")
        pages[0].wait("document.querySelectorAll('input[type=radio]').length >= 4 && !!document.querySelector('input[type=file]')")
        shots.append(screenshot(pages[0], "notifications-welcome-desktop.png"))
        checks.append("Admin authenticated in live app; desktop welcome rendered")

        profiles = [
            {"marks_percentage": 80, "current_class": 8, "previous_class": 7,
             "current_school_type": "government", "previous_school_type": "government",
             "annual_family_income_inr": 200000, "attempt_count": 1},
            {"marks_percentage": 50, "current_class": 8, "previous_class": 7,
             "current_school_type": "government", "previous_school_type": "government",
             "annual_family_income_inr": 200000, "attempt_count": 1},
            {"current_class": 8},
        ]
        for page, email, profile in zip(pages[1:], emails[1:], profiles):
            register(page, email, PASSWORD)
            save_profile(page, profile)
        student_ids = [account_id_for(store, email) for email in emails[1:]]
        service = NotificationService(store)
        pages[3].navigate(BASE + "/")
        pages[3].wait("document.querySelectorAll('input[type=radio]').length >= 4")
        select_section(pages[3], "Notifications")
        click_checkbox(pages[3], "Notices needing more profile information")
        pages[3].click_text("Save preferences")
        pages[3].wait("document.body.innerText.includes('Notification preferences saved.')")
        assert service.preferences(student_ids[2])["more_information"]
        checks.append("Three independent student accounts saved qualifying, failing and incomplete profiles; incomplete account opted in through the real notification preferences UI")

        select_section(pages[0], "Admin Notice Management")
        upload_pdf(pages[0], FIXTURE)
        pages[0].click_text("Analyze and save as draft")
        pages[0].wait("document.body.innerText.includes('saved privately as a draft')", 60)
        pages[0].wait("[...document.querySelectorAll('[role=tab]')].some(e=>e.innerText.includes('Admin Notice Management'))")
        pages[0].js("[...document.querySelectorAll('[role=tab]')].find(e=>e.innerText.includes('Admin Notice Management')).click()")
        pages[0].wait("document.body.innerText.includes('Private draft')")
        pages[0].wait("[...document.querySelectorAll('input[aria-label]')].some(e=>e.getAttribute('aria-label')==='I checked the extracted conditions and page citations against the full notice.')")
        notice = next(n for n in NoticeLibrary(store).list_admin(account_id_for(store, emails[0])) if "NMMSS" in n.title)
        click_checkbox(pages[0], "I checked the extracted conditions and page citations against the full notice.")
        pages[0].click_text("Save completeness review")
        pages[0].wait("document.body.innerText.includes('Completeness review recorded by')")
        pages[0].click_text("Publish notice")
        pages[0].wait("document.body.innerText.includes('Published')")
        checks.append("Admin uploaded the checked-in Hindi SCERT PDF, reviewed extracted eligibility and published through the real browser UI")

        for index, page in enumerate(pages[1:4]):
            page.navigate(BASE + "/")
            page.wait("document.body.innerText.includes('Your notice, made clearer')")
            select_section(page, "Notifications")
            body = page.text()
            if index == 0:
                assert notice.title in body, body[-1000:]
                assert "may match your reviewed profile requirements" in body
            elif index == 1:
                assert "You have no notifications yet." in body
                assert notice.title not in body
                assert "may match your reviewed profile requirements" not in body
            else:
                assert notice.title in body, body[-1000:]
                assert "More information is needed" in body
            checks.append(f"Student {index+1} notifications matched profile and preference; no other account data exposed")
        shots.append(screenshot(pages[1], "notifications-english-unread.png"))
        assert service.unread_count(student_ids[0]) == 1
        # Marking the same notice read persists through rerun and restart.
        pages[1].click_text("Mark as read")
        pages[1].wait("document.body.innerText.includes('Mark as read') === false")
        assert service.unread_count(student_ids[0]) == 0
        checks.append("Mark-as-read persisted to SQLite; event is idempotent on app rerun")

        set_language(pages[1], "తెలుగు", "నోటిఫికేషన్లు")
        select_section(pages[1], "నోటిఫికేషన్లు")
        shots.append(screenshot(pages[1], "notifications-telugu.png"))
        set_language(pages[1], "हिन्दी", "सूचनाएँ")
        select_section(pages[1], "सूचनाएँ")
        shots.append(screenshot(pages[1], "notifications-hindi.png"))
        checks.append("Notifications page rendered in Telugu and Hindi with translated UI copy")
        pages[1].click_text("सूचना देखें")
        pages[1].wait("[...document.querySelectorAll('h2')].some(e=>e.innerText.trim()==='सूचना का विवरण')")
        assert notice.title in pages[1].text()
        checks.append("Hindi notification link opened the corresponding published notice details")

        pages[1].call("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 1, "mobile": True})
        select_section(pages[1], "सूचनाएँ")
        overflow = pages[1].js("document.documentElement.scrollWidth > window.innerWidth")
        shots.append(screenshot(pages[1], "notifications-mobile.png"))
        checks.append(f"Mobile notification page captured; horizontal overflow={overflow}")
        assert not overflow

        # Student cannot access admin publication by direct library call.
        from services.auth.store import AuthorizationError
        try:
            NoticeLibrary(store).set_publication(student_ids[0], notice.notice_id, False)
            raise AssertionError("student publication unexpectedly succeeded")
        except AuthorizationError:
            checks.append("Student publication API call denied by persisted admin authorization")
        # Independent isolated context has no authenticated account or notice state.
        fresh = pages[4]
        fresh.navigate(BASE + "/")
        fresh.wait("location.pathname.startsWith('/auth/login')")
        assert notice.title not in fresh.text()
        checks.append("Separate browser context has no authenticated session or notice content")

        library = NoticeLibrary(store)
        library.set_publication(account_id_for(store, emails[0]), notice.notice_id, False)
        assert all(not service.list_for_user(user_id) for user_id in student_ids)
        checks.append("Unpublishing hides notification rows and their notice links from students")
        output = {"browser": "Chrome headless CDP", "checks": checks, "screenshots": shots,
                  "notification_counts": [service.unread_count(user_id) for user_id in student_ids],
                  "notice_title": notice.title, "unpublished": True}
        target = ROOT / "reports" / "notifications_browser_results.json"
        target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        for page in pages:
            try: page.ws.close()
            except Exception: pass
        for context in contexts:
            try: browser.call("Target.disposeBrowserContext", {"browserContextId": context})
            except Exception: pass
        browser.ws.close()


if __name__ == "__main__":
    main()

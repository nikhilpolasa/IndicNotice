"""HTTP authorization, CSRF, account lifecycle and cross-user isolation tests."""
from __future__ import annotations

from pathlib import Path
import re

from fastapi.testclient import TestClient

from services.auth.gateway import GatewaySettings, create_app

ORIGIN = "http://testserver"
PASSWORD = "Correct Horse Battery 812!"
SETTINGS = GatewaySettings(public_origin=ORIGIN, streamlit_port=8599,
                           secure_cookie=False, allowed_hosts=("testserver",))


def csrf(html: str) -> str:
    match = re.search(r'<input type="hidden" name="csrf" value="([^"]+)"', html)
    assert match
    return match.group(1)


def register(client: TestClient, email: str, *, lang: str = "en"):
    page = client.get(f"/auth/register?lang={lang}")
    assert page.status_code == 200
    return client.post("/auth/register", data={
        "csrf": csrf(page.text), "lang": lang, "email": email,
        "password": PASSWORD, "confirm_password": PASSWORD,
    }, headers={"Origin": ORIGIN})


def test_registration_login_logout_duplicate_and_csrf_protection(tmp_path: Path):
    app = create_app(database_path=tmp_path / "accounts.sqlite3", settings=SETTINGS)
    with TestClient(app, base_url=ORIGIN, follow_redirects=False) as client:
        assert client.get("/account/profile").status_code == 303
        registered = register(client, "student@example.org", lang="te")
        assert registered.status_code == 303
        assert registered.headers["location"] == "/account/profile?welcome=1"
        session_cookie = registered.headers.get("set-cookie", "")
        assert "HttpOnly" in session_cookie and "SameSite=strict" in session_cookie
        assert client.get("/api/session").json() == {"email": "student@example.org", "preferred_language": "te"}
        assert "నా ప్రొఫైల్" in client.get("/account/profile").text

        logout_page = client.get("/auth/logout")
        logged_out = client.post("/auth/logout", data={"csrf": csrf(logout_page.text)}, headers={"Origin": ORIGIN})
        assert logged_out.status_code == 303
        assert client.get("/api/session").status_code == 401
        assert client.get("/account/profile").status_code == 303

        duplicate = register(client, "STUDENT@example.org")
        assert duplicate.status_code == 200 and "An account already exists" in duplicate.text

        login_page = client.get("/auth/login")
        bad = client.post("/auth/login", data={"csrf": csrf(login_page.text), "email": "student@example.org", "password": "wrong"}, headers={"Origin": ORIGIN})
        assert "Email or password is incorrect." in bad.text
        login_page = client.get("/auth/login")
        missing_origin = client.post("/auth/login", data={"csrf": csrf(login_page.text), "email": "student@example.org", "password": PASSWORD})
        assert "form expired" in missing_origin.text

        login_page = client.get("/auth/login")
        good = client.post("/auth/login", data={"csrf": csrf(login_page.text), "email": "student@example.org", "password": PASSWORD}, headers={"Origin": ORIGIN})
        assert good.status_code == 303 and client.get("/api/session").status_code == 200


def test_profiles_are_private_editable_persistent_and_deleteable(tmp_path: Path):
    database = tmp_path / "accounts.sqlite3"
    app = create_app(database_path=database, settings=SETTINGS)
    with TestClient(app, base_url=ORIGIN, follow_redirects=False) as a, TestClient(app, base_url=ORIGIN, follow_redirects=False) as b:
        assert register(a, "a@example.org").status_code == 303
        assert register(b, "b@example.org").status_code == 303
        profile_page = a.get("/account/profile")
        saved = a.post("/account/profile", data={
            "csrf": csrf(profile_page.text), "profile_current_class": "8",
            "profile_marks_percentage": "84.5", "include_income": "1",
            "profile_annual_family_income_inr": "250000", "custom_key": "language_preference",
            "custom_value": "te",
        }, headers={"Origin": ORIGIN})
        assert saved.status_code == 303
        edited_page = a.get(saved.headers["location"])
        assert "84.5" in edited_page.text and "language_preference" in edited_page.text
        assert "84.5" not in b.get("/account/profile").text
        assert b.get("/api/session").json()["email"] == "b@example.org"

        # A service restart reuses the same SQLite schema and session records.
        restarted = create_app(database_path=database, settings=SETTINGS)
        with TestClient(restarted, base_url=ORIGIN, cookies={"indicnotice_session": a.cookies.get("indicnotice_session"), "indicnotice_csrf": a.cookies.get("indicnotice_csrf")}, follow_redirects=False) as after_restart:
            assert after_restart.get("/api/session").status_code == 200
            assert after_restart.get("/account/profile").status_code == 200

        deletion_page = a.get("/account/profile")
        deleted_profile = a.post("/account/profile/delete", data={"csrf": csrf(deletion_page.text)}, headers={"Origin": ORIGIN})
        assert deleted_profile.status_code == 303
        assert "No profile details are saved" in a.get(deleted_profile.headers["location"]).text

        settings_page = a.get("/account/settings")
        result = a.post("/account/delete", data={"csrf": csrf(settings_page.text), "confirmation": "DELETE", "password": PASSWORD}, headers={"Origin": ORIGIN})
        assert result.status_code == 303
        assert a.get("/api/session").status_code == 401
        assert b.get("/api/session").status_code == 200

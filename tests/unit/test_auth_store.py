"""Authentication persistence, hashing, expiry and isolation contract tests."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.auth.store import (
    AuthStore, DuplicateAccount, InvalidCredentials, PasswordPolicyError,
    SESSION_TTL_SECONDS, hash_password, verify_password,
)


PASSWORD = "Correct Horse Battery 812!"


def test_password_hash_is_salted_scrypt_and_never_plaintext():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)
    assert first.startswith("scrypt$32768$8$1$")
    assert first != second
    assert PASSWORD not in first
    assert verify_password(PASSWORD, first)
    assert not verify_password("incorrect password", first)
    with pytest.raises(PasswordPolicyError):
        hash_password("short")


def test_register_duplicate_login_and_password_persistence(tmp_path: Path):
    database = tmp_path / "accounts.sqlite3"
    store = AuthStore(database)
    account = store.register("Student@example.org", PASSWORD)
    assert account["email"] == "Student@example.org"
    with pytest.raises(DuplicateAccount):
        store.register("student@EXAMPLE.org", PASSWORD)
    assert store.login("STUDENT@example.org", PASSWORD)["account_id"] == account["account_id"]
    with pytest.raises(InvalidCredentials):
        store.login("student@example.org", "incorrect password")
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT password_hash FROM accounts").fetchone()
        versions = connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    assert row and row[0].startswith("scrypt$") and PASSWORD not in row[0]
    assert versions == [(1,), (2,), (3,), (4,)]


def test_server_side_sessions_expire_revoke_and_survive_store_restart(tmp_path: Path):
    database = tmp_path / "accounts.sqlite3"
    first_store = AuthStore(database)
    account = first_store.register("one@example.org", PASSWORD)
    token, expires = first_store.create_session(account["account_id"], now=1_000)
    assert expires == 1_000 + SESSION_TTL_SECONDS
    with sqlite3.connect(database) as connection:
        assert token not in str(connection.execute("SELECT session_hash FROM sessions").fetchone())
    restarted_store = AuthStore(database)
    assert restarted_store.account_for_session(token, now=1_001)["account_id"] == account["account_id"]
    expired_token, _ = restarted_store.create_session(account["account_id"], now=1_000)
    assert restarted_store.account_for_session(expired_token, now=expires) is None
    assert restarted_store.account_for_session(token, now=1_001) is not None
    restarted_store.revoke_session(token)
    assert restarted_store.account_for_session(token, now=1_001) is None


def test_profile_update_delete_and_account_cascade(tmp_path: Path):
    store = AuthStore(tmp_path / "accounts.sqlite3")
    account = store.register("profile@example.org", PASSWORD)
    user_id = account["account_id"]
    store.replace_profile(user_id, {"current_class": 8, "state_region": "తెలంగాణ", "annual_family_income_inr": 200000})
    assert store.get_profile(user_id) == {"annual_family_income_inr": 200000, "current_class": 8, "state_region": "తెలంగాణ"}
    store.replace_profile(user_id, {"current_class": 9})
    assert store.get_profile(user_id) == {"current_class": 9}
    store.update_language(user_id, "hi")
    assert store.account_by_id(user_id)["preferred_language"] == "hi"
    store.delete_profile(user_id)
    assert store.get_profile(user_id) == {}
    token, _ = store.create_session(user_id)
    assert store.delete_account(user_id, "wrong") is False
    assert store.delete_account(user_id, PASSWORD) is True
    assert store.account_for_session(token) is None
    assert store.account_for_session(token) is None
    with sqlite3.connect(store.database_path) as connection:
        assert connection.execute("SELECT count(*) FROM profile_attributes").fetchone()[0] == 0


def test_profile_records_are_scoped_by_unique_account_id(tmp_path: Path):
    store = AuthStore(tmp_path / "accounts.sqlite3")
    a = store.register("a@example.org", PASSWORD)
    b = store.register("b@example.org", PASSWORD)
    assert a["account_id"] != b["account_id"]
    store.replace_profile(a["account_id"], {"marks_percentage": 77.5})
    assert store.get_profile(a["account_id"]) == {"marks_percentage": 77.5}
    assert store.get_profile(b["account_id"]) == {}


def test_rate_limit_bucket_resets_only_after_its_window(tmp_path: Path):
    store = AuthStore(tmp_path / "accounts.sqlite3")
    store.record_attempt("key", window_seconds=300, now=100)
    store.record_attempt("key", window_seconds=300, now=101)
    assert not store.is_rate_limited("key", limit=3, window_seconds=300, now=200)
    store.record_attempt("key", window_seconds=300, now=102)
    assert store.is_rate_limited("key", limit=3, window_seconds=300, now=200)
    assert not store.is_rate_limited("key", limit=3, window_seconds=300, now=400)

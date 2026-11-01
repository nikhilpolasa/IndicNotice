"""SQLite account store with scrypt password hashes and opaque server sessions."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Iterator
from uuid import uuid4


SESSION_TTL_SECONDS = 12 * 60 * 60
SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LENGTH = 32
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DUMMY_SALT = b"indicnotice-auth-dummy-salt"


class DuplicateAccount(ValueError):
    pass


class InvalidCredentials(ValueError):
    pass


class PasswordPolicyError(ValueError):
    pass


class AuthorizationError(PermissionError):
    """The signed-in account is not allowed to perform this operation."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_email(email: str) -> str:
    value = email.strip().casefold()
    if len(value) > 254 or not EMAIL_RE.fullmatch(value):
        raise ValueError("Enter a valid email address.")
    return value


def validate_password(password: str) -> None:
    if len(password) < 12:
        raise PasswordPolicyError("Use at least 12 characters for your password.")
    if len(password) > 1024:
        raise PasswordPolicyError("Password is too long.")


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    validate_password(password)
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R,
        p=SCRYPT_P, dklen=SCRYPT_LENGTH, maxmem=64 * 1024 * 1024,
    )
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N, SCRYPT_R, SCRYPT_P,
        _b64(salt), _b64(digest),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$")
        if algorithm != "scrypt":
            return False
        expected = _unb64(digest_text)
        calculated = hashlib.scrypt(
            password.encode("utf-8"), salt=_unb64(salt_text),
            n=int(n), r=int(r), p=int(p), dklen=len(expected),
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(calculated, expected)
    except (ValueError, TypeError, OverflowError):
        return False


def _b64(value: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    import base64
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def session_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()


class AuthStore:
    """Stateless SQLite access; each method owns a short-lived connection."""

    def __init__(self, database_path: str | Path | None = None):
        default = Path(__file__).resolve().parents[2] / ".data" / "indicnotice.sqlite3"
        configured = database_path or os.environ.get("INDICNOTICE_AUTH_DB") or default
        self.database_path = str(configured)
        if self.database_path != ":memory:":
            path = Path(self.database_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.database_path = str(path)
            if os.name != "nt":
                path.parent.chmod(0o700)
        self._migrate()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=5, isolation_level="DEFERRED")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("BEGIN IMMEDIATE")
            # Parse complete SQL statements so every migration and version marker
            # commit together. sqlite3.executescript() implicitly commits first.
            sql_dir = Path(__file__).parent / "migrations"
            for migration in sorted(sql_dir.glob("[0-9][0-9][0-9]_*.sql")):
                version = int(migration.name[:3])
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
                ).fetchone()
                if exists and connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version=?", (version,)
                ).fetchone():
                    continue
                pending = ""
                for line in migration.read_text(encoding="utf-8").splitlines():
                    pending += line + "\n"
                    if sqlite3.complete_statement(pending):
                        if pending.strip():
                            connection.execute(pending)
                        pending = ""
                if pending.strip():
                    raise RuntimeError(f"Incomplete SQL migration: {migration.name}")
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                    (version, utc_now()),
                )
        if self.database_path != ":memory:" and os.name != "nt":
            Path(self.database_path).chmod(0o600)

    def register(self, email: str, password: str) -> dict:
        normalized = normalize_email(email)
        password_hash = hash_password(password)
        account_id = str(uuid4())
        now = utc_now()
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO accounts(account_id,email,email_normalized,password_hash,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (account_id, email.strip(), normalized, password_hash, now, now),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateAccount("An account already exists for this email address.") from exc
        return self.account_by_id(account_id)

    def login(self, email: str, password: str) -> dict:
        try:
            normalized = normalize_email(email)
        except ValueError:
            normalized = email.strip().casefold()[:254]
        with self._connect() as connection:
            account = connection.execute("SELECT * FROM accounts WHERE email_normalized=?", (normalized,)).fetchone()
        if account is None:
            hashlib.scrypt(password.encode("utf-8")[:1024], salt=DUMMY_SALT, n=SCRYPT_N,
                           r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_LENGTH, maxmem=64 * 1024 * 1024)
            raise InvalidCredentials("Email or password is incorrect.")
        if not verify_password(password[:1024], account["password_hash"]):
            raise InvalidCredentials("Email or password is incorrect.")
        return self._account_dict(account)

    def create_session(self, account_id: str, *, now: int | None = None) -> tuple[str, int]:
        token = secrets.token_urlsafe(32)
        created = int(time.time()) if now is None else now
        expires = created + SESSION_TTL_SECONDS
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (created,))
            connection.execute("INSERT INTO sessions(session_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)",
                               (session_digest(token), account_id, created, expires))
        return token, expires

    def account_for_session(self, token: str | None, *, now: int | None = None) -> dict | None:
        if not token or len(token) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
            return None
        timestamp = int(time.time()) if now is None else now
        digest = session_digest(token)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT a.*, s.expires_at FROM sessions s JOIN accounts a ON a.account_id=s.account_id "
                "WHERE s.session_hash=? AND s.expires_at>?", (digest, timestamp),
            ).fetchone()
            if row is None:
                connection.execute("DELETE FROM sessions WHERE session_hash=? AND expires_at<=?", (digest, timestamp))
                return None
            return self._account_dict(row)

    def revoke_session(self, token: str | None) -> None:
        if token:
            with self._connect() as connection:
                connection.execute("DELETE FROM sessions WHERE session_hash=?", (session_digest(token),))

    def account_by_id(self, account_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM accounts WHERE account_id=?", (account_id,)).fetchone()
        if row is None:
            raise ValueError("Account does not exist.")
        return self._account_dict(row)

    @staticmethod
    def _account_dict(row: sqlite3.Row) -> dict:
        return {key: row[key] for key in (
            "account_id", "email", "preferred_language", "created_at", "updated_at", "is_admin",
        )}

    def is_admin(self, account_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT is_admin FROM accounts WHERE account_id=?", (account_id,)).fetchone()
        return bool(row and row["is_admin"])

    def grant_admin(self, email: str, password: str) -> None:
        """Promote a locally authenticated account; used only by the operator CLI."""
        account = self.login(email, password)
        with self._connect() as connection:
            connection.execute(
                "UPDATE accounts SET is_admin=1,updated_at=? WHERE account_id=?",
                (utc_now(), account["account_id"]),
            )

    def get_profile(self, account_id: str) -> dict[str, object]:
        with self._connect() as connection:
            rows = connection.execute("SELECT attribute_key,value_json FROM profile_attributes WHERE account_id=? ORDER BY attribute_key", (account_id,)).fetchall()
        return {row["attribute_key"]: json.loads(row["value_json"]) for row in rows}

    def replace_profile(self, account_id: str, attributes: dict[str, object]) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute("DELETE FROM profile_attributes WHERE account_id=?", (account_id,))
            connection.executemany(
                "INSERT INTO profile_attributes(account_id,attribute_key,value_json,updated_at) VALUES(?,?,?,?)",
                [(account_id, key, json.dumps(value, ensure_ascii=False, separators=(",", ":")), now)
                 for key, value in sorted(attributes.items())],
            )
            connection.execute("UPDATE accounts SET updated_at=? WHERE account_id=?", (now, account_id))
        from services.auth.notifications import NotificationService
        NotificationService(self).reconcile_user(account_id)

    def delete_profile(self, account_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM profile_attributes WHERE account_id=?", (account_id,))
            connection.execute("UPDATE accounts SET updated_at=? WHERE account_id=?", (utc_now(), account_id))
        from services.auth.notifications import NotificationService
        NotificationService(self).reconcile_user(account_id)

    def update_language(self, account_id: str, language: str) -> None:
        if language not in {"en", "te", "hi"}:
            raise ValueError("Choose English, Telugu or Hindi.")
        with self._connect() as connection:
            connection.execute("UPDATE accounts SET preferred_language=?,updated_at=? WHERE account_id=?",
                               (language, utc_now(), account_id))

    def change_password(self, account_id: str, current_password: str, new_password: str) -> bool:
        account = self.account_by_id(account_id)
        with self._connect() as connection:
            row = connection.execute("SELECT password_hash FROM accounts WHERE account_id=?", (account_id,)).fetchone()
        if row is None or not verify_password(current_password[:1024], row["password_hash"]):
            return False
        new_hash = hash_password(new_password)
        with self._connect() as connection:
            connection.execute("UPDATE accounts SET password_hash=?,updated_at=? WHERE account_id=?",
                               (new_hash, utc_now(), account_id))
            connection.execute("DELETE FROM sessions WHERE account_id=?", (account_id,))
        return True

    def delete_account(self, account_id: str, current_password: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT password_hash FROM accounts WHERE account_id=?", (account_id,)).fetchone()
        if row is None or not verify_password(current_password[:1024], row["password_hash"]):
            return False
        with self._connect() as connection:
            connection.execute("DELETE FROM accounts WHERE account_id=?", (account_id,))
        return True

    def is_rate_limited(self, bucket_key: str, *, limit: int, window_seconds: int, now: int | None = None) -> bool:
        timestamp = int(time.time()) if now is None else now
        with self._connect() as connection:
            row = connection.execute("SELECT window_started_at,attempts FROM auth_limits WHERE bucket_key=?", (bucket_key,)).fetchone()
        return bool(row and row["window_started_at"] + window_seconds > timestamp and row["attempts"] >= limit)

    def record_attempt(self, bucket_key: str, *, window_seconds: int, now: int | None = None) -> None:
        timestamp = int(time.time()) if now is None else now
        with self._connect() as connection:
            row = connection.execute("SELECT window_started_at,attempts FROM auth_limits WHERE bucket_key=?", (bucket_key,)).fetchone()
            if row is None or row["window_started_at"] + window_seconds <= timestamp:
                connection.execute("INSERT INTO auth_limits(bucket_key,window_started_at,attempts) VALUES(?,?,1) "
                                   "ON CONFLICT(bucket_key) DO UPDATE SET window_started_at=excluded.window_started_at,attempts=1",
                                   (bucket_key, timestamp))
            else:
                connection.execute("UPDATE auth_limits SET attempts=attempts+1 WHERE bucket_key=?", (bucket_key,))

    def clear_attempts(self, bucket_key: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM auth_limits WHERE bucket_key=?", (bucket_key,))

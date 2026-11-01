CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    email_normalized TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    preferred_language TEXT NOT NULL DEFAULT 'en' CHECK (preferred_language IN ('en', 'te', 'hi')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE sessions (
    session_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE INDEX sessions_by_account ON sessions(account_id);
CREATE INDEX sessions_by_expiry ON sessions(expires_at);

CREATE TABLE profile_attributes (
    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    attribute_key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(account_id, attribute_key)
);

CREATE TABLE auth_limits (
    bucket_key TEXT PRIMARY KEY,
    window_started_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

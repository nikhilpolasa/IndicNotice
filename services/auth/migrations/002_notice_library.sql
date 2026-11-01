ALTER TABLE accounts ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1));

CREATE TABLE notice_library (
    notice_id TEXT PRIMARY KEY,
    document_sha256 TEXT NOT NULL UNIQUE,
    storage_key TEXT NOT NULL,
    owner_id TEXT REFERENCES accounts(account_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    issuing_authority TEXT,
    source_url TEXT,
    source_language TEXT,
    publication_date TEXT,
    deadlines_json TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    publication_state TEXT NOT NULL DEFAULT 'draft' CHECK (publication_state IN ('draft', 'published')),
    eligibility_reviewed INTEGER NOT NULL DEFAULT 0 CHECK (eligibility_reviewed IN (0, 1)),
    uploaded_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX notice_library_publication ON notice_library(publication_state, published_at DESC);
CREATE INDEX notice_library_owner ON notice_library(owner_id, uploaded_at DESC);
CREATE INDEX notice_library_deadlines ON notice_library(publication_date);

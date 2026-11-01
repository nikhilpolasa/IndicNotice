ALTER TABLE notice_library ADD COLUMN eligibility_reviewed_by TEXT REFERENCES accounts(account_id) ON DELETE SET NULL;
ALTER TABLE notice_library ADD COLUMN eligibility_reviewed_at TEXT;

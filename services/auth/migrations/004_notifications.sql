CREATE TABLE notification_preferences (
    account_id TEXT PRIMARY KEY REFERENCES accounts(account_id) ON DELETE CASCADE,
    relevant_notices INTEGER NOT NULL DEFAULT 1 CHECK (relevant_notices IN (0, 1)),
    more_information INTEGER NOT NULL DEFAULT 0 CHECK (more_information IN (0, 1)),
    reminder_7_days INTEGER NOT NULL DEFAULT 1 CHECK (reminder_7_days IN (0, 1)),
    reminder_3_days INTEGER NOT NULL DEFAULT 1 CHECK (reminder_3_days IN (0, 1)),
    reminder_1_day INTEGER NOT NULL DEFAULT 1 CHECK (reminder_1_day IN (0, 1)),
    updated_at TEXT NOT NULL
);

CREATE TABLE notifications (
    notification_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    notice_id TEXT NOT NULL REFERENCES notice_library(notice_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('relevant_notice', 'more_information', 'deadline')),
    reminder_days INTEGER NOT NULL DEFAULT 0 CHECK (reminder_days IN (0, 1, 3, 7)),
    created_at TEXT NOT NULL,
    read_at TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    UNIQUE(user_id, notice_id, event_type, reminder_days)
);
CREATE INDEX notifications_user_unread ON notifications(user_id, active, read_at, created_at DESC);
CREATE INDEX notifications_notice ON notifications(notice_id, active);

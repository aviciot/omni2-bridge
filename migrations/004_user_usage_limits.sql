-- ============================================================
-- User Usage Limits
-- ============================================================
-- Stores per-user usage caps and reset windows.

CREATE TABLE IF NOT EXISTS user_usage_limits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_days INTEGER NOT NULL DEFAULT 30,
    max_requests INTEGER,
    max_tokens INTEGER,
    max_cost NUMERIC(12, 4),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_reset_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_usage_limits_user_id
    ON user_usage_limits(user_id);

CREATE INDEX IF NOT EXISTS idx_user_usage_limits_active
    ON user_usage_limits(is_active);

COMMENT ON TABLE user_usage_limits IS 'Per-user usage limits (requests/tokens/cost) with reset windows.';
COMMENT ON COLUMN user_usage_limits.period_days IS 'Window size in days for usage limits.';
COMMENT ON COLUMN user_usage_limits.last_reset_at IS 'Start time for current usage window.';

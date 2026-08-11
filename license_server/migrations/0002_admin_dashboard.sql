CREATE TABLE IF NOT EXISTS admin_login_attempts (
    id VARCHAR(36) PRIMARY KEY,
    address_hash VARCHAR(64) NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_admin_login_attempt_address_time
    ON admin_login_attempts(address_hash, attempted_at);

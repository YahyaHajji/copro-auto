CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS licenses (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
    key_digest VARCHAR(64) NOT NULL UNIQUE,
    key_hint VARCHAR(12) NOT NULL,
    plan VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    seat_limit INTEGER NOT NULL CHECK (seat_limit > 0),
    trial BOOLEAN NOT NULL,
    commercial_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_licenses_organization_id ON licenses(organization_id);

CREATE TABLE IF NOT EXISTS activations (
    id VARCHAR(36) PRIMARY KEY,
    license_id VARCHAR(36) NOT NULL REFERENCES licenses(id),
    device_hash VARCHAR(64) NOT NULL,
    device_label VARCHAR(160) NOT NULL,
    secret_digest VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL,
    app_version VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    deactivated_at TIMESTAMPTZ,
    CONSTRAINT uq_license_device UNIQUE (license_id, device_hash)
);

CREATE INDEX IF NOT EXISTS ix_activations_license_id ON activations(license_id);
CREATE INDEX IF NOT EXISTS ix_activation_license_status ON activations(license_id, status);

CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    license_id VARCHAR(36),
    activation_id VARCHAR(36),
    details TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS ix_audit_events_license_id ON audit_events(license_id);

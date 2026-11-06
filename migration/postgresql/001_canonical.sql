CREATE SCHEMA IF NOT EXISTS rcatlas;

CREATE TABLE rcatlas.workspace (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    version bigint NOT NULL CHECK (version >= 0),
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK ((payload->>'workspace_version')::bigint = version)
);
INSERT INTO rcatlas.workspace(singleton, version, payload)
VALUES (true, 0, '{"workspace_version":0}');

-- Integrity rows are derived from the canonical document in the SAME transaction.
-- They are never hydrated back into the document or independently edited by APIs.
CREATE TABLE rcatlas.organizations (
    id text PRIMARY KEY CHECK (id <> '')
);
CREATE TABLE rcatlas.entities (
    kind text NOT NULL,
    id text NOT NULL CHECK (id <> ''),
    organization_id text REFERENCES rcatlas.organizations(id) DEFERRABLE INITIALLY DEFERRED,
    project_id text,
    attributes jsonb NOT NULL,
    idempotency_active boolean NOT NULL DEFAULT false,
    owner_key text GENERATED ALWAYS AS (coalesce(organization_id,'')) STORED,
    PRIMARY KEY(kind, id, owner_key),
    UNIQUE NULLS NOT DISTINCT(kind, id, organization_id),
    CHECK (organization_id IS NOT NULL OR kind IN ('audit_events','dashboard_templates'))
);
CREATE TABLE rcatlas.relationships (
    source_kind text NOT NULL,
    source_id text NOT NULL,
    organization_id text NOT NULL,
    field text NOT NULL,
    target_kind text NOT NULL,
    target_id text NOT NULL,
    PRIMARY KEY(source_kind, source_id, organization_id, field, target_kind, target_id),
    FOREIGN KEY(source_kind, source_id, organization_id)
        REFERENCES rcatlas.entities(kind,id,organization_id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(target_kind, target_id, organization_id)
        REFERENCES rcatlas.entities(kind,id,organization_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX entities_tenant_kind ON rcatlas.entities(organization_id,kind);
CREATE UNIQUE INDEX users_username ON rcatlas.entities(lower(attributes->>'username'))
    WHERE kind='users';
CREATE UNIQUE INDEX sessions_token ON rcatlas.entities((attributes->>'token_hash'))
    WHERE kind='sessions';
CREATE UNIQUE INDEX idempotency_scope ON rcatlas.entities
    (organization_id,(attributes->>'actor_user_id'),(attributes->>'operation'),(attributes->>'key_hash'))
    WHERE kind='idempotency_records' AND idempotency_active;
CREATE UNIQUE INDEX project_code_scope ON rcatlas.entities
    (organization_id,lower(attributes->>'project_code'))
    WHERE kind='projects' AND coalesce(attributes->>'project_code','') <> '';

CREATE TABLE rcatlas.import_receipts (
    source_sha256 text PRIMARY KEY,
    payload_sha256 text NOT NULL,
    imported_version bigint NOT NULL,
    counts jsonb NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

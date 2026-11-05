CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS content_hash CHAR(64);

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS document_number TEXT,
    ADD COLUMN IF NOT EXISTS searchable_blob_name TEXT,
    ADD COLUMN IF NOT EXISTS document_date DATE,
    ADD COLUMN IF NOT EXISTS subject TEXT,
    ADD COLUMN IF NOT EXISTS issuing_office TEXT,
    ADD COLUMN IF NOT EXISTS referenced_documents JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS metadata_confidence NUMERIC(4,3),
    ADD COLUMN IF NOT EXISTS metadata_status TEXT NOT NULL DEFAULT 'unavailable';

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS ocr_confidence NUMERIC(4,3),
    ADD COLUMN IF NOT EXISTS uncertain_regions INTEGER NOT NULL DEFAULT 0;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS layout_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS processing_completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS processing_error TEXT;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'reviewer';

CREATE TABLE IF NOT EXISTS document_audit_events (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS document_audit_events_document_idx
    ON document_audit_events(document_id, created_at DESC);

    CREATE TABLE IF NOT EXISTS evaluation_cases (
        id BIGSERIAL PRIMARY KEY,
        document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        page_number INTEGER NOT NULL,
        expected_text TEXT NOT NULL,
        expected_document_number TEXT,
        expected_date DATE,
        expected_subject TEXT,
        expected_issuing_office TEXT,
        expected_region JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(document_id, page_number)
    );

    CREATE INDEX IF NOT EXISTS evaluation_cases_user_idx
    ON evaluation_cases(user_id);

    CREATE TABLE IF NOT EXISTS search_evaluation_cases (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        query TEXT NOT NULL,
        expected_document_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
        last_success BOOLEAN,
        last_run_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS documents_document_number_idx
    ON documents(document_number);

CREATE INDEX IF NOT EXISTS documents_date_idx
    ON documents(document_date);

CREATE TABLE IF NOT EXISTS document_regions (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    x0 REAL NOT NULL,
    y0 REAL NOT NULL,
    x1 REAL NOT NULL,
    y1 REAL NOT NULL,
    confidence NUMERIC(4,3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS document_regions_lookup_idx
    ON document_regions(document_id, page_number);

CREATE TABLE IF NOT EXISTS document_metadata_corrections (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    previous_values JSONB NOT NULL,
    corrected_values JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS document_metadata_corrections_document_idx
    ON document_metadata_corrections(document_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS documents_user_content_hash_idx
    ON documents(user_id, content_hash)
    WHERE content_hash IS NOT NULL AND user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    replaced_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS refresh_tokens_user_idx
    ON refresh_tokens(user_id);

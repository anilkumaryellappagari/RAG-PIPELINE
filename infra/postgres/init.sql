-- Spec items 2 and 3: initialize document job-state storage.

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    s3_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'done', 'failed')),
    error TEXT,
    page_count INT,
    chunk_count INT,
    entity_count INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_status
    ON documents(status);

CREATE INDEX IF NOT EXISTS idx_documents_created_at
    ON documents(created_at);

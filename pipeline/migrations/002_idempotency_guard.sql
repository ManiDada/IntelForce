-- Migration 002: Idempotency guard for pipeline runs

CREATE TABLE IF NOT EXISTS pipeline_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

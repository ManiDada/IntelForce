-- Migration 001: Core jobs table and supporting tables

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    budget TEXT,
    budget_min REAL,
    budget_max REAL,
    budget_type TEXT,
    experience_level TEXT,
    duration TEXT,
    client_rating REAL,
    client_spent TEXT,
    client_location TEXT,
    proposals_count INTEGER,
    skills TEXT,
    posted_time TEXT,
    url TEXT,
    status TEXT DEFAULT 'discovered',
    score REAL,
    score_breakdown TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scored_at TIMESTAMP,
    proposal_generated_at TIMESTAMP,
    proposal_sent_at TIMESTAMP,
    won_at TIMESTAMP,
    delivered_at TIMESTAMP,
    raw_data TEXT
);

CREATE TABLE IF NOT EXISTS skills_tracker (
    skill TEXT PRIMARY KEY,
    current_level INTEGER,
    target_level INTEGER,
    jobs_completed INTEGER DEFAULT 0,
    last_practiced TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_metrics (
    date TEXT PRIMARY KEY,
    jobs_discovered INTEGER DEFAULT 0,
    jobs_scored INTEGER DEFAULT 0,
    proposals_sent INTEGER DEFAULT 0,
    responses_received INTEGER DEFAULT 0,
    jobs_won INTEGER DEFAULT 0,
    revenue REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS proposals_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    version INTEGER DEFAULT 1,
    proposal_text TEXT,
    sent_at TIMESTAMP,
    response TEXT,
    response_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS client_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    rating REAL,
    review_text TEXT,
    received_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill TEXT,
    activity TEXT,
    duration_minutes INTEGER,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pipeline_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    score REAL NOT NULL,
    confidence REAL NOT NULL,
    gate_decision TEXT NOT NULL,
    proposal_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

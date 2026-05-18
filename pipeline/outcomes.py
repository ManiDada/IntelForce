"""Outcome logging for pipeline runs."""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone


def log_outcome(conn: sqlite3.Connection, job_id: str, outcome: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO pipeline_outcomes (job_id, outcome, detail) VALUES (?, ?, ?)",
        (job_id, outcome, detail),
    )
    conn.commit()


def log_approval(
    conn: sqlite3.Connection, job_id: str, stage: str, decision: str, reason: str = ""
) -> None:
    conn.execute(
        "INSERT INTO pipeline_approvals (job_id, stage, decision, reason) VALUES (?, ?, ?, ?)",
        (job_id, stage, decision, reason),
    )
    conn.commit()


def log_proposal(
    conn: sqlite3.Connection,
    job_id: str,
    score: float,
    confidence: float,
    gate_decision: str,
    proposal_text: str,
) -> None:
    conn.execute(
        """INSERT INTO pipeline_proposals
           (job_id, score, confidence, gate_decision, proposal_text)
           VALUES (?, ?, ?, ?, ?)""",
        (job_id, score, confidence, gate_decision, proposal_text),
    )
    conn.commit()


def is_duplicate(conn: sqlite3.Connection, idempotency_key: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pipeline_idempotency WHERE idempotency_key = ?",
        (idempotency_key,),
    ).fetchone()
    return row is not None


def mark_processed(conn: sqlite3.Connection, idempotency_key: str, job_id: str, stage: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO pipeline_idempotency (idempotency_key, job_id, stage) VALUES (?, ?, ?)",
        (idempotency_key, job_id, stage),
    )
    conn.commit()


def update_daily_metrics(conn: sqlite3.Connection, **kwargs: int) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO daily_metrics (date) VALUES (?) ON CONFLICT(date) DO NOTHING",
        (today,),
    )
    for col, val in kwargs.items():
        conn.execute(
            f"UPDATE daily_metrics SET {col} = {col} + ? WHERE date = ?",
            (val, today),
        )
    conn.commit()

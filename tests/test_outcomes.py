"""Tests for outcome logging."""
import pytest
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.db import apply_migrations
from pipeline.outcomes import (
    log_outcome, log_approval, log_proposal,
    is_duplicate, mark_processed, update_daily_metrics,
)


@pytest.fixture
def conn():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        c = sqlite3.connect(f.name)
        c.row_factory = sqlite3.Row
        apply_migrations(c)
        yield c
        c.close()


def test_log_outcome(conn):
    log_outcome(conn, "job_001", "queued_for_review", "EV >= 70")
    rows = conn.execute("SELECT * FROM pipeline_outcomes WHERE job_id='job_001'").fetchall()
    assert len(rows) == 1
    assert rows[0]["outcome"] == "queued_for_review"


def test_log_approval(conn):
    log_approval(conn, "job_001", "propose", "REVIEW_AND_SEND", "qualified")
    rows = conn.execute("SELECT * FROM pipeline_approvals WHERE job_id='job_001'").fetchall()
    assert len(rows) == 1
    assert rows[0]["decision"] == "REVIEW_AND_SEND"


def test_idempotency_guard(conn):
    key = "upwork:job_001:propose"
    assert not is_duplicate(conn, key)
    mark_processed(conn, key, "job_001", "propose")
    assert is_duplicate(conn, key)


def test_idempotency_allows_different_keys(conn):
    mark_processed(conn, "upwork:job_001:propose", "job_001", "propose")
    assert not is_duplicate(conn, "upwork:job_001:score")
    assert not is_duplicate(conn, "upwork:job_002:propose")


def test_daily_metrics_accumulate(conn):
    update_daily_metrics(conn, jobs_discovered=5)
    update_daily_metrics(conn, jobs_scored=3)
    update_daily_metrics(conn, jobs_discovered=2)
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute("SELECT * FROM daily_metrics WHERE date=?", (today,)).fetchone()
    assert row["jobs_discovered"] == 7
    assert row["jobs_scored"] == 3

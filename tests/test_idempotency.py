"""Tests for pipeline idempotency — safe to run twice."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_pipeline_skips_duplicate_on_rerun(tmp_path):
    """Running the pipeline twice on the same jobs.json must not double-process."""
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(
        '{"jobs":[{"id":"test_idem_001","platform":"upwork","title":"API integration test",'
        '"required_skills":"python,api","proposals_count":5,"budget_min":500,"status":"discovered"}]}',
        encoding="utf-8",
    )
    db_file = tmp_path / "data" / "jobs.db"
    db_file.parent.mkdir()

    os.environ["JOBS_JSON_PATH"] = str(jobs_file)

    from pipeline.db import get_connection, apply_migrations
    from pipeline.runner import run_pipeline

    # Monkey-patch the DB path and proposals dir
    import pipeline.db as db_mod
    import pipeline.runner as runner_mod

    orig_db = db_mod.DEFAULT_DB
    orig_pending = runner_mod.PENDING_DIR

    db_mod.DEFAULT_DB = db_file
    runner_mod.PENDING_DIR = tmp_path / "proposals" / "pending"
    runner_mod.PENDING_DIR.mkdir(parents=True)

    try:
        r1 = run_pipeline(limit=10, dry_run=False, gate_mode="manual")
        r2 = run_pipeline(limit=10, dry_run=False, gate_mode="manual")
        assert r1["processed"] >= 1
        assert r2["skipped_duplicate"] >= 1 or r2["processed"] == 0
    finally:
        db_mod.DEFAULT_DB = orig_db
        runner_mod.PENDING_DIR = orig_pending
        del os.environ["JOBS_JSON_PATH"]

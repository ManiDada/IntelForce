"""Load and normalize jobs from jobs.json into the database."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sqlite3

from .db import upsert_job
from .models import Job

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOBS_JSON = ROOT / "data" / "jobs.json"


def load_jobs_from_json(path: Path | None = None) -> list[Job]:
    src = Path(os.environ.get("JOBS_JSON_PATH", str(path or DEFAULT_JOBS_JSON)))
    if not src.exists():
        return []
    raw = json.loads(src.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("jobs", [raw])
    return [Job.from_dict(d) for d in raw if isinstance(d, dict) and d.get("id")]


def ingest_jobs(conn: sqlite3.Connection, jobs: list[Job]) -> int:
    count = 0
    for job in jobs:
        upsert_job(conn, job.to_dict())
        count += 1
    return count


def load_unscored_jobs(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status IN ('discovered','qualified') "
        "AND score IS NULL ORDER BY discovered_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]

"""SQLite connection and migration runner."""
from __future__ import annotations
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "jobs.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def apply_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations "
        "(name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    conn.commit()

    applied = {row[0] for row in conn.execute("SELECT name FROM _migrations")}
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for f in migration_files:
        if f.name in applied:
            continue
        sql = f.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute("INSERT INTO _migrations (name) VALUES (?)", (f.name,))
        conn.commit()


def upsert_job(conn: sqlite3.Connection, job_dict: dict) -> None:
    conn.execute(
        """
        INSERT INTO jobs (
            id, platform, title, description, budget, budget_min, budget_max,
            budget_type, experience_level, duration, client_rating, client_spent,
            client_location, proposals_count, skills, posted_time, url, status, raw_data
        ) VALUES (
            :id, :platform, :title, :description, :budget, :budget_min, :budget_max,
            :budget_type, :experience_level, :duration, :client_rating, :client_spent,
            :client_location, :proposals_count, :skills, :posted_time, :url,
            :status, :raw_data
        )
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            proposals_count=excluded.proposals_count,
            status=CASE WHEN jobs.status='discovered' THEN excluded.status ELSE jobs.status END
        """,
        {
            "id": job_dict.get("id"),
            "platform": job_dict.get("platform", "upwork"),
            "title": job_dict.get("title", ""),
            "description": job_dict.get("description", ""),
            "budget": job_dict.get("budget", ""),
            "budget_min": job_dict.get("budget_min"),
            "budget_max": job_dict.get("budget_max"),
            "budget_type": job_dict.get("budget_type", "fixed"),
            "experience_level": job_dict.get("experience_level", ""),
            "duration": job_dict.get("duration", ""),
            "client_rating": job_dict.get("client_rating"),
            "client_spent": job_dict.get("client_spent", ""),
            "client_location": job_dict.get("client_location", ""),
            "proposals_count": job_dict.get("proposals_count", 0),
            "skills": job_dict.get("skills", job_dict.get("required_skills", "")),
            "posted_time": job_dict.get("posted_time", ""),
            "url": job_dict.get("url", ""),
            "status": job_dict.get("status", "discovered"),
            "raw_data": str(job_dict),
        },
    )
    conn.commit()

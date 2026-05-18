"""Pipeline orchestrator: discovery → scoring → proposal → gate → log."""
from __future__ import annotations
import json
from pathlib import Path

from .db import get_connection, apply_migrations
from .ingestion import load_jobs_from_json, ingest_jobs, load_unscored_jobs
from .models import Job, ProposalDraft
from .scoring import score_job_dict
from .proposal import build_human_proposal
from .approval import gate_decision_with_job
from .outcomes import (
    log_outcome, log_approval, log_proposal, is_duplicate,
    mark_processed, update_daily_metrics,
)

ROOT = Path(__file__).resolve().parents[1]
PENDING_DIR = ROOT / "proposals" / "pending"


def run_pipeline(
    limit: int = 20,
    gate_mode: str = "manual",
    dry_run: bool = True,
    allow_send: bool = False,
) -> dict:
    """Run the full pipeline. Returns a summary dict."""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    apply_migrations(conn)

    jobs_from_file = load_jobs_from_json()
    ingested = ingest_jobs(conn, jobs_from_file)
    update_daily_metrics(conn, jobs_discovered=ingested)

    raw_jobs = load_unscored_jobs(conn, limit=limit)

    results = {
        "ingested": ingested,
        "processed": 0,
        "proposals_generated": 0,
        "auto_send_eligible": 0,
        "queued_for_review": 0,
        "held": 0,
        "skipped_duplicate": 0,
        "dry_run": dry_run,
        "gate_mode": gate_mode,
        "proposals": [],
    }

    for raw in raw_jobs:
        job = Job.from_dict(dict(raw))
        idempotency_key = f"{job.platform}:{job.id}:propose"

        if is_duplicate(conn, idempotency_key):
            results["skipped_duplicate"] += 1
            log_outcome(conn, job.id, "skipped_duplicate", "already processed")
            continue

        score_data = score_job_dict(raw)

        if score_data["red_flags"]:
            results["held"] += 1
            log_outcome(conn, job.id, "held", "red flags detected")
            conn.execute(
                "UPDATE jobs SET status='qualified', score=?, score_breakdown=?, scored_at=datetime('now') WHERE id=?",
                (score_data["ev"], json.dumps(score_data), job.id),
            )
            conn.commit()
            continue

        proposal_text, confidence = build_human_proposal(raw, score_data)
        decision, reason = gate_decision_with_job(score_data["ev"], confidence, raw, gate_mode)

        draft = ProposalDraft(
            job_id=job.id,
            score=score_data["ev"],
            confidence=confidence,
            gate_decision=decision,
            gate_reason=reason,
            proposal_text=proposal_text,
            skill_score=score_data["skill_score"],
            win_probability=score_data["win_probability"],
            ev=score_data["ev"],
        )

        if not dry_run:
            filepath = PENDING_DIR / draft.filename
            filepath.write_text(proposal_text, encoding="utf-8")

            log_proposal(conn, job.id, score_data["ev"], confidence, decision, proposal_text)
            log_approval(conn, job.id, "propose", decision, reason)
            mark_processed(conn, idempotency_key, job.id, "propose")

            conn.execute(
                "UPDATE jobs SET status='proposal_ready', score=?, score_breakdown=?, "
                "scored_at=datetime('now'), proposal_generated_at=datetime('now') WHERE id=?",
                (score_data["ev"], json.dumps(score_data), job.id),
            )
            conn.commit()

        outcome_key = {
            "AUTO_SEND_ELIGIBLE": "auto_send_eligible",
            "REVIEW_AND_SEND": "queued_for_review",
            "HOLD": "held",
        }.get(decision, "held")

        if not dry_run:
            log_outcome(conn, job.id, outcome_key, reason)
            update_daily_metrics(conn, jobs_scored=1)
            if decision != "HOLD":
                update_daily_metrics(conn, proposals_sent=1)

        results[outcome_key] += 1
        results["processed"] += 1
        if decision != "HOLD":
            results["proposals_generated"] += 1

        results["proposals"].append({
            "job_id": job.id,
            "title": job.title,
            "ev": score_data["ev"],
            "confidence": confidence,
            "decision": decision,
            "reason": reason,
            "filename": draft.filename if not dry_run else "(dry-run)",
        })

    conn.close()
    return results

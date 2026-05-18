#!/usr/bin/env python3
"""Generate proposals for all scored jobs above threshold.

Usage:
    python3 scripts/proposal_generator.py
    python3 scripts/proposal_generator.py --min-score 70 --job-id upwork_abc123
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.db import get_connection, apply_migrations
from pipeline.scoring import score_job_dict
from pipeline.proposal import build_human_proposal
from pipeline.approval import gate_decision_with_job
from pipeline.outcomes import log_proposal, log_approval, log_outcome

PENDING = ROOT / "proposals" / "pending"


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Generate proposals for scored jobs")
    parser.add_argument("--min-score", type=float, default=60.0)
    parser.add_argument("--job-id", help="Generate for a specific job ID only")
    parser.add_argument("--gate-mode", default="manual")
    args = parser.parse_args()

    PENDING.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    apply_migrations(conn)

    if args.job_id:
        rows = [conn.execute("SELECT * FROM jobs WHERE id=?", (args.job_id,)).fetchone()]
        rows = [r for r in rows if r]
    else:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE score >= ? AND status IN ('scored','discovered','qualified') "
            "ORDER BY score DESC",
            (args.min_score,),
        ).fetchall()

    if not rows:
        print("No jobs found above threshold.")
        return 0

    print(f"\n📝 Generating proposals for {len(rows)} jobs\n{'='*60}")
    generated = 0

    for row in rows:
        job = dict(row)
        title = job.get("title", "?")[:60]
        score_data = score_job_dict(job)
        proposal_text, confidence = build_human_proposal(job, score_data)
        decision, reason = gate_decision_with_job(score_data["ev"], confidence, job, args.gate_mode)

        safe_id = job["id"].replace("/", "_").replace(":", "_")
        filename = f"{datetime.now().strftime('%Y-%m-%d')}_{safe_id}.md"
        filepath = PENDING / filename
        filepath.write_text(proposal_text, encoding="utf-8")

        log_proposal(conn, job["id"], score_data["ev"], confidence, decision, proposal_text)
        log_approval(conn, job["id"], "propose", decision, reason)
        log_outcome(conn, job["id"], "queued_for_review" if decision != "HOLD" else "held", reason)

        conn.execute(
            "UPDATE jobs SET status='proposal_ready', proposal_generated_at=datetime('now') WHERE id=?",
            (job["id"],),
        )
        conn.commit()

        icon = "✅" if confidence >= 85 else "⚠️ " if confidence >= 60 else "🔴"
        print(f"{icon} {title}")
        print(f"   EV: {score_data['ev']:.1f} | Confidence: {confidence:.0f}% | Decision: {decision}")
        print(f"   → proposals/pending/{filename}")
        generated += 1

    conn.close()
    print(f"\n✅ Generated {generated} proposals in proposals/pending/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

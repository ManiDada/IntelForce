#!/usr/bin/env python3
"""Standalone job scorer — score a single job or all unscored jobs in the DB.

Usage:
    python3 scripts/job_scorer.py --all
    python3 scripts/job_scorer.py --job-id upwork_abc123
    python3 scripts/job_scorer.py --json '{"title":"n8n workflow","required_skills":"n8n,python","proposals_count":5}'
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.db import get_connection, apply_migrations
from pipeline.scoring import score_job_dict, score_root


def score_and_print(job: dict) -> None:
    ev_result = score_job_dict(job)
    root_score, breakdown = score_root(job)
    print(f"\n{'='*60}")
    print(f"Job: {job.get('title','?')[:70]}")
    print(f"{'='*60}")
    print(f"  EV score:        {ev_result['ev']:.1f}")
    print(f"  Job score:       {ev_result['job_score']:.1f}")
    print(f"  Skill score:     {ev_result['skill_score']:.1f}%")
    print(f"  Win probability: {ev_result['win_probability']:.1f}%")
    print(f"  Speed score:     {ev_result['speed_score']:.1f}")
    print(f"  Root score:      {root_score:.1f}/100")
    print(f"  Red flags:       {'YES ⚠️' if ev_result['red_flags'] else 'No'}")
    gate = "REVIEW_AND_SEND" if ev_result["ev"] >= 70 else "HOLD"
    print(f"  Gate decision:   {gate}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Upwork jobs")
    parser.add_argument("--all", action="store_true", help="Score all unscored jobs in DB")
    parser.add_argument("--job-id", help="Score a specific job by ID")
    parser.add_argument("--json", help="Score a job from a JSON string")
    parser.add_argument("--min-score", type=float, default=0, help="Only show jobs above this EV")
    args = parser.parse_args()

    if args.json:
        job = json.loads(args.json)
        score_and_print(job)
        return 0

    conn = get_connection()
    apply_migrations(conn)

    if args.job_id:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (args.job_id,)).fetchone()
        if not row:
            print(f"Job not found: {args.job_id}")
            return 1
        score_and_print(dict(row))
    elif args.all:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE score IS NULL ORDER BY discovered_at DESC"
        ).fetchall()
        print(f"Scoring {len(rows)} unscored jobs...")
        for row in rows:
            d = dict(row)
            result = score_job_dict(d)
            root_score, breakdown = score_root(d)
            if result["ev"] >= args.min_score:
                score_and_print(d)
            conn.execute(
                "UPDATE jobs SET score=?, score_breakdown=?, status='scored', scored_at=datetime('now') WHERE id=?",
                (result["ev"], json.dumps(result), d["id"]),
            )
        conn.commit()
        print(f"\n✅ Scored {len(rows)} jobs")
    else:
        parser.print_help()

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

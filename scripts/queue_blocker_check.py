#!/usr/bin/env python3
"""Detect pipeline stalls and emit governance state.

Exit code 1 when blocked (scored candidates exist but nothing is in active build lane).
Usage:
    python3 scripts/queue_blocker_check.py
    python3 scripts/queue_blocker_check.py --json > /tmp/governance.json
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GOVERNANCE_FILE = ROOT / "data" / "queue-governance-state.json"
ACTIVE_STATUSES = ("won", "build_ready", "building")
MIN_SCORED_TO_TRIGGER = 1


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--min-scored", type=int, default=MIN_SCORED_TO_TRIGGER)
    args = parser.parse_args()

    from pipeline.db import get_connection, apply_migrations
    conn = get_connection()
    apply_migrations(conn)

    counts = dict(conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())
    active_count = sum(counts.get(s, 0) for s in ACTIVE_STATUSES)
    scored_count = counts.get("scored", 0) + counts.get("proposal_ready", 0)
    pending_proposals = len(list((ROOT / "proposals" / "pending").glob("*.md"))) if (ROOT / "proposals" / "pending").exists() else 0

    top_scored = conn.execute(
        "SELECT id, title, status, score FROM jobs WHERE score IS NOT NULL ORDER BY score DESC LIMIT 5"
    ).fetchall()

    blocked = scored_count >= args.min_scored and active_count == 0
    now = datetime.now(timezone.utc)

    state = {
        "blocked": blocked,
        "checked_at": now.isoformat(),
        "active_build_lane": active_count,
        "scored_candidates": scored_count,
        "pending_proposals": pending_proposals,
        "status_counts": counts,
        "top_scored": [
            {"id": r[0], "title": r[1][:60], "status": r[2], "score": r[3]}
            for r in top_scored
        ],
    }

    if blocked:
        state["escalation_level"] = "critical"
        state["recommended_action"] = (
            "Escalate to operator: scored proposals exist but no active build lane. "
            "Review proposals/pending/ and approve submissions."
        )

    GOVERNANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    GOVERNANCE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(state, indent=2))
        return 1 if blocked else 0

    print(f"Queue Governance Check — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}")
    print(f"  Blocked:              {'YES 🔴' if blocked else 'No ✅'}")
    print(f"  Active build lane:    {active_count}")
    print(f"  Scored candidates:    {scored_count}")
    print(f"  Pending proposals:    {pending_proposals}")
    print(f"\nStatus breakdown:")
    for status, count in sorted(counts.items()):
        print(f"  {status:20s} {count}")
    if top_scored:
        print(f"\nTop scored jobs:")
        for r in top_scored:
            print(f"  [{r[3]:.1f}] {r[1][:55]} ({r[2]})")
    if blocked:
        print(f"\n⚠️  ESCALATION REQUIRED: {state['recommended_action']}")

    conn.close()
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())

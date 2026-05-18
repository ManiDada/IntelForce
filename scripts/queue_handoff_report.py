#!/usr/bin/env python3
"""Generate a QA handoff report for a won job.

Usage:
    python3 scripts/queue_handoff_report.py --job-id upwork_abc123
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--out", default=None, help="Output file path (default: qa-reports/<job_id>.md)")
    args = parser.parse_args()

    from pipeline.db import get_connection, apply_migrations
    conn = get_connection()
    apply_migrations(conn)

    row = conn.execute("SELECT * FROM jobs WHERE id=?", (args.job_id,)).fetchone()
    if not row:
        print(f"Job not found: {args.job_id}")
        return 1

    job = dict(row)
    proposal_row = conn.execute(
        "SELECT proposal_text, confidence FROM pipeline_proposals WHERE job_id=? ORDER BY created_at DESC LIMIT 1",
        (args.job_id,),
    ).fetchone()

    out_path = Path(args.out) if args.out else ROOT / "qa-reports" / f"{args.job_id}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = f"""# QA Handoff Report: {job.get('title', '?')}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Job Summary
- **ID:** {job['id']}
- **Platform:** {job.get('platform', '?')}
- **Status:** {job.get('status', '?')}
- **Score:** {job.get('score', '?')}
- **Budget:** {job.get('budget', '?')}
- **URL:** {job.get('url', '?')}

## Proposal Promises
Review the accepted proposal before starting build. Every promise is an acceptance criterion.

{proposal_row[0] if proposal_row else '(no proposal found)'}

## QA Checklist

- [ ] All promised deliverables shipped
- [ ] Scope creep blocked or documented as change request
- [ ] Deterministic test cases pass
- [ ] Failure modes tested and documented (API failure, timeout, retry)
- [ ] Security: secrets in env vars, no hardcoded credentials
- [ ] Client-operable documentation complete (README, runbook, troubleshooting)
- [ ] Handoff package assembled

## Delivery Package Structure

```
{job['id']}/
├── README.md
├── .env.example
├── src/
├── tests/
├── docs/
│   ├── SETUP.md
│   ├── USER-GUIDE.md
│   └── TESTING.md
├── deliverables/
│   └── TEST-REPORT.md
└── delivery-notes.md
```
"""

    out_path.write_text(report, encoding="utf-8")
    print(f"✅ Report saved: {out_path}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

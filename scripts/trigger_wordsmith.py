#!/usr/bin/env python3
"""
Bridge: reads scored GO decisions from jobs.json and generates proposals via Wordsmith.
Runs after score_and_notify.py in the Viper pipeline.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NOTIFIED_FILE = ROOT / "data" / "notified_jobs.json"
WORDSMITH_QUEUE = ROOT / "data" / "wordsmith_queue.json"


def main() -> int:
    jobs_file = ROOT / "data" / "jobs.json"
    if not jobs_file.exists():
        return 0

    notified = set()
    if NOTIFIED_FILE.exists():
        notified = set(json.loads(NOTIFIED_FILE.read_text()))

    wordsmith_done = set()
    if WORDSMITH_QUEUE.exists():
        try:
            q = json.loads(WORDSMITH_QUEUE.read_text())
            wordsmith_done = set(q.get("processed", []))
        except Exception:
            pass

    data = json.loads(jobs_file.read_text())
    jobs = data.get("jobs", []) if isinstance(data, dict) else data

    # Find jobs that were notified (scored GO) but don't have proposals yet
    pending_dir = ROOT / "proposals" / "pending"
    existing_proposals = {p.stem.split("_", 1)[-1] for p in pending_dir.glob("*.md")} if pending_dir.exists() else set()

    queue = []
    for job in jobs:
        job_id = job.get("id", "")
        if job_id not in notified:
            continue
        if job_id in wordsmith_done:
            continue
        safe_id = job_id.replace("/", "_").replace(":", "_")
        if any(safe_id in p for p in existing_proposals):
            continue
        queue.append(job)

    if not queue:
        print("[WORDSMITH TRIGGER] No new jobs to draft proposals for")
        return 0

    print(f"[WORDSMITH TRIGGER] {len(queue)} jobs need proposals")

    env = {}
    env_file = ROOT / "secrets" / "viper.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    bot_token = env.get("WORDSMITH_BOT_TOKEN", "")
    chat_id = env.get("WORDSMITH_CHAT_ID", "")

    for job in queue[:3]:  # Max 3 proposals per Viper run
        try:
            from scripts.generate_proposal import generate_proposal, send_approval_request
            proposal_text, confidence = generate_proposal(job)
            print(f"  ✓ Draft ready: {job['title'][:50]} (conf: {confidence:.0f}%)")

            # Save to pending
            from datetime import datetime
            pending_dir.mkdir(parents=True, exist_ok=True)
            safe_id = job["id"].replace("/", "_").replace(":", "_")
            out = pending_dir / f"{datetime.now().strftime('%Y-%m-%d')}_{safe_id}.md"
            out.write_text(proposal_text)

            # Send to Telegram for approval
            if bot_token and chat_id:
                send_approval_request(job, proposal_text, confidence, bot_token, chat_id)

            wordsmith_done.add(job["id"])
        except Exception as e:
            print(f"  ✗ Error for {job.get('title','?')[:40]}: {e}", file=sys.stderr)

    # Save progress
    WORDSMITH_QUEUE.write_text(json.dumps({"processed": list(wordsmith_done)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

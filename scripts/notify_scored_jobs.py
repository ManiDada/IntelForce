#!/usr/bin/env python3
"""Send high-EV job alerts via cortextos bus Telegram."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOBS_FILE = ROOT / "data" / "jobs.json"
NOTIFIED_FILE = ROOT / "data" / "notified_jobs.json"
SCORES_LOG = ROOT / "data" / "scores.log"
SCORING_CONFIG = ROOT / "config" / "scoring_config.json"

EV_THRESHOLD = 70
DAILY_CAP = 8
TELEGRAM_CHAT_ID = "8893758382"


def load_scoring_config() -> dict:
    try:
        return json.loads(SCORING_CONFIG.read_text())
    except Exception:
        return {}


def load_notified() -> set:
    if not NOTIFIED_FILE.exists():
        return set()
    try:
        data = json.loads(NOTIFIED_FILE.read_text())
        return set(data) if isinstance(data, list) else set()
    except Exception:
        return set()


def save_notified(notified: set) -> None:
    NOTIFIED_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTIFIED_FILE.write_text(json.dumps(sorted(notified), indent=2), encoding="utf-8")


def append_scores_log(entries: list[dict]) -> None:
    SCORES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SCORES_LOG.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def build_message(job: dict) -> str:
    ev = job.get("ev") or job.get("expected_value", 0)
    title = job.get("title", "Untitled")
    url = job.get("url", "")
    desc = job.get("description", "")[:200]

    budget_min = job.get("budget_min")
    budget_max = job.get("budget_max")
    if budget_min and budget_max and budget_min != budget_max:
        budget_display = f"${budget_min:,.0f}–${budget_max:,.0f}"
    elif budget_min:
        budget_display = f"${budget_min:,.0f}"
    else:
        budget_display = "Not stated"

    discovered_at = job.get("discovered_at", "")
    if discovered_at:
        try:
            dt = datetime.fromisoformat(discovered_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            delta = now - dt
            hours = int(delta.total_seconds() // 3600)
            age_display = f"{hours}h ago" if hours < 48 else f"{delta.days}d ago"
        except Exception:
            age_display = discovered_at[:10]
    else:
        age_display = "Unknown"

    return (
        f"NEW JOB — EV: {ev}/100\n\n"
        f"{title}\n"
        f"Budget: {budget_display} | Posted: {age_display}\n\n"
        f"{desc}\n\n"
        f"{url}"
    )


def send_telegram(message: str, dry_run: bool) -> None:
    if dry_run:
        print("--- DRY RUN MESSAGE ---")
        print(message)
        print("--- END ---\n")
        return
    subprocess.run(
        ["cortextos", "bus", "send-telegram", TELEGRAM_CHAT_ID, message],
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify high-EV jobs via Telegram")
    parser.add_argument("--dry-run", action="store_true", help="Print messages without sending")
    args = parser.parse_args()

    if not JOBS_FILE.exists():
        print(f"[NOTIFY] No jobs file at {JOBS_FILE}", file=sys.stderr)
        return 1

    try:
        data = json.loads(JOBS_FILE.read_text())
        all_jobs = data.get("jobs", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"[NOTIFY] Failed to read jobs.json: {e}", file=sys.stderr)
        return 1

    notified = load_notified()

    # Cold start mode filter
    cfg = load_scoring_config()
    ev_threshold = cfg.get("score_threshold_ev", EV_THRESHOLD)
    max_proposals = cfg.get("max_competing_proposals")
    red_flag_keywords = [kw.lower() for kw in cfg.get("red_flag_keywords", [])]

    def _passes_cold_start_filter(j: dict) -> bool:
        if max_proposals is not None:
            if int(j.get("competing_proposals") or j.get("proposals_count") or 0) > max_proposals:
                return False
        if red_flag_keywords:
            text = f"{j.get('title', '')} {j.get('description', '')}".lower()
            if any(kw in text for kw in red_flag_keywords):
                return False
        return True

    eligible = [
        j for j in all_jobs
        if (j.get("ev") or j.get("expected_value") or 0) >= ev_threshold
        and j.get("id") not in notified
        and _passes_cold_start_filter(j)
    ]
    eligible.sort(key=lambda j: j.get("ev") or j.get("expected_value") or 0, reverse=True)
    batch = eligible[:DAILY_CAP]

    print(f"[NOTIFY] {len(eligible)} eligible jobs, sending top {len(batch)}")

    now_iso = datetime.now(timezone.utc).isoformat()
    log_entries = []
    newly_notified = set()

    for job in batch:
        msg = build_message(job)
        send_telegram(msg, args.dry_run)
        job_id = job.get("id", "")
        title = job.get("title", "")
        ev = job.get("ev") or job.get("expected_value") or 0
        if job_id:
            newly_notified.add(job_id)
        log_entries.append({"job_id": job_id, "title": title, "ev": ev, "notified_at": now_iso})

    if not args.dry_run:
        save_notified(notified | newly_notified)
        append_scores_log(log_entries)
        print(f"[NOTIFY] Sent {len(batch)} notifications, updated notified_jobs.json")
    else:
        append_scores_log(log_entries)
        print(f"[NOTIFY] Dry run complete — {len(batch)} messages printed, scores.log appended")

    return 0


if __name__ == "__main__":
    sys.exit(main())

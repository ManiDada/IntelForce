#!/usr/bin/env python3
"""
Viper's scoring + notification pipeline.
Reads jobs.json, scores each job, sends Telegram alerts for qualifying ones.

Usage: python3 scripts/score_and_notify.py [--dry-run] [--snipe-only]
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NOTIFIED_FILE = ROOT / "data" / "notified_jobs.json"
SNIPE_FILE = ROOT / "data" / "snipe_alerts.json"
CONFIG_FILE = ROOT / "config" / "scoring_config.json"

# Viper's Telegram config (loaded from .env)
def get_viper_config():
    env_file = ROOT / "secrets" / "viper.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
    return {
        "bot_token": os.getenv("VIPER_BOT_TOKEN", ""),
        "chat_id": os.getenv("VIPER_CHAT_ID", ""),
    }


def load_scoring_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {
        "score_threshold_ev": 65,
        "max_competing_proposals": 15,
        "budget_min_gbp": 100,
        "budget_max_gbp": 500,
        "daily_cap": 8,
        "skill_weight": 0.80,
        "competition_weight": 0.20,
        "speed_weight": 0.0,
        "portfolio_penalty": -15,
        "portfolio_items": 2,
        "portfolio_keywords": ["portfolio", "previous work", "examples", "loom", "show us", "similar work"],
        "red_flag_keywords": ["complex", "multi-step", "code", "script", "several", "custom code"],
    }


MY_SKILLS = {
    "python": 85, "api": 85, "api integration": 85, "automation": 85,
    "web scraping": 80, "scraping": 80, "beautifulsoup": 80, "playwright": 80,
    "openai": 80, "claude": 80, "gpt": 80, "ai": 75, "llm": 75,
    "javascript": 80, "node.js": 80, "nodejs": 80,
    "webhooks": 75, "rest": 75, "integration": 75,
    "zapier": 70, "workflow": 70, "database": 75, "sql": 75,
    "chatbot": 75, "bot": 75, "discord": 70, "slack": 70, "telegram": 75,
    "stripe": 75, "payment": 70, "data": 70, "pandas": 75,
    "make": 50, "make.com": 50, "integromat": 50,
    "n8n": 40, "n8n workflow": 40,
    "crm": 50, "hubspot": 35, "salesforce": 40, "zoho": 40,
    "langchain": 60, "rag": 65, "vector": 65,
    "airtable": 60, "notion": 60, "google sheets": 70,
    "google": 65, "sheets": 70,
}


def skill_score(required_skills: str) -> float:
    if not required_skills:
        return 60.0
    import re
    skills = [s.strip().lower() for s in re.split(r"[,;/]", required_skills)]
    if not skills:
        return 60.0
    total = sum(MY_SKILLS.get(s, 30) for s in skills)
    return round(min(100.0, total / len(skills)), 1)


def score_job(job: dict, config: dict) -> dict:
    """EV scoring model (cold-start weights: skill 80%, competition 20%, speed 0%)."""
    skill = skill_score(job.get("required_skills", job.get("skills", "")))
    competition = int(job.get("proposals_count") or 0)
    win_prob = max(10.0, 95.0 - min(80.0, competition * 1.2))
    speed = 90.0 if competition <= 10 else 65.0 if competition <= 30 else 40.0

    sw = config.get("skill_weight", 0.80)
    cw = config.get("competition_weight", 0.20)
    ev = round((sw * skill) + (cw * win_prob), 1)

    # Portfolio penalty
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    portfolio_kws = config.get("portfolio_keywords", [])
    portfolio_count = config.get("portfolio_items", 0)
    if portfolio_count < 2 and any(k in text for k in portfolio_kws):
        ev = round(ev + config.get("portfolio_penalty", -15), 1)

    # Budget bonus
    bmax = job.get("budget_max") or job.get("budget_min") or 0
    if bmax >= 500:
        ev = round(min(100, ev + 5), 1)
    elif bmax >= 200:
        ev = round(min(100, ev + 2), 1)

    # Client quality bonus
    client_spent = job.get("client_spent", "")
    if client_spent and ("K" in client_spent or "M" in client_spent):
        ev = round(min(100, ev + 3), 1)
    if job.get("client_verified"):
        ev = round(min(100, ev + 2), 1)

    return {
        "ev": ev,
        "skill_score": skill,
        "win_probability": win_prob,
        "speed_score": speed,
        "red_flags": has_red_flags(job, config),
    }


def has_red_flags(job: dict, config: dict) -> bool:
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    red_flags = config.get("red_flag_keywords", [])
    generic = ["cheapest", "lowest price", "simple task", "quick fix", "equity only", "revenue share only"]
    return any(rf in text for rf in red_flags + generic)


def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    if not bot_token or not chat_id:
        print(f"  [NOTIFY] no token/chat_id configured", file=sys.stderr)
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f"  [NOTIFY] telegram error: {e}", file=sys.stderr)
        return False


def format_proposal_request(job: dict, score: dict) -> str:
    ev = score["ev"]
    skill = score["skill_score"]
    win_prob = score["win_probability"]
    competition = int(job.get("proposals_count") or 0)
    budget = job.get("budget") or f"£{job.get('budget_min','?')}–{job.get('budget_max','?')}"
    client_spent = job.get("client_spent") or "unknown"
    title = job["title"][:70]
    url = job.get("url", "")
    snipe = "🔴 SNIPE" if competition <= 5 else "📋 REVIEW"

    return (
        f"{snipe} — *{title}*\n\n"
        f"EV: {ev:.0f} | Skill: {skill:.0f}% | Win: {win_prob:.0f}%\n"
        f"Budget: {budget} | Competition: {competition} proposals\n"
        f"Client: {client_spent} spent | Verified: {'✓' if job.get('client_verified') else '✗'}\n\n"
        f"[View Job]({url})\n\n"
        f"Wordsmith drafting proposal now..."
    )


def load_notified() -> set:
    if NOTIFIED_FILE.exists():
        return set(json.loads(NOTIFIED_FILE.read_text()))
    return set()


def save_notified(notified: set):
    NOTIFIED_FILE.write_text(json.dumps(list(notified)))


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--snipe-only", action="store_true")
    parser.add_argument("--limit", type=int, default=8, help="Max notifications per run")
    args = parser.parse_args()

    config = load_scoring_config()
    viper = get_viper_config()
    notified = load_notified()

    jobs_file = ROOT / "data" / "jobs.json"
    if not jobs_file.exists():
        print("No jobs.json found. Run scanner first.")
        return 0

    data = json.loads(jobs_file.read_text())
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    unscored = [j for j in jobs if j.get("status") == "discovered" and j["id"] not in notified]

    print(f"[SCORE+NOTIFY] {len(unscored)} unnotified jobs to score")
    sent = 0

    for job in unscored:
        if sent >= args.limit:
            break

        score = score_job(job, config)

        if score["red_flags"]:
            print(f"  SKIP (red flags): {job['title'][:50]}")
            notified.add(job["id"])  # Skip permanently
            continue

        ev = score["ev"]
        competition = int(job.get("proposals_count") or 0)

        # Hard filter
        if competition > config.get("max_competing_proposals", 15):
            print(f"  SKIP (competition {competition}): {job['title'][:50]}")
            notified.add(job["id"])
            continue

        if ev < config.get("score_threshold_ev", 65):
            print(f"  HOLD (EV {ev:.0f}): {job['title'][:50]}")
            notified.add(job["id"])
            continue

        # GO decision
        is_snipe = competition <= 5
        print(f"  {'🔴 SNIPE' if is_snipe else '✅ GO'} (EV {ev:.0f}, {competition} props): {job['title'][:50]}")

        if not args.dry_run:
            msg = format_proposal_request(job, score)
            send_telegram(viper["bot_token"], viper["chat_id"], msg)
            notified.add(job["id"])
            sent += 1

    if not args.dry_run:
        save_notified(notified)

    print(f"[SCORE+NOTIFY] sent {sent} notifications")
    return 0


if __name__ == "__main__":
    sys.exit(main())

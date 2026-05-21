#!/usr/bin/env python3
"""
Wordsmith's proposal generator.
Reads voice.md + case studies, generates an authentic proposal for a given job.

Usage:
    python3 scripts/generate_proposal.py --job-id <id>
    python3 scripts/generate_proposal.py --json '{"title":"...","description":"..."}'
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

VOICE_FILE = ROOT / "voice" / "voice.md"
CASE_STUDIES_DIR = ROOT / "build-packs"
PENDING_DIR = ROOT / "proposals" / "pending"

# Slop detector patterns
SLOP_PATTERNS = [
    "experienced developer", "efficiently and effectively", "i look forward to working",
    "i am confident that", "please feel free to", "i have extensive experience",
    "i would be happy to", "seamless integration", "end-to-end solution",
    "robust and scalable", "tailor-made", "cutting-edge", "leverage", "utilize",
    "looking forward to", "happy to help", "don't hesitate", "reach out",
]


def detect_job_type(job: dict) -> str:
    text = f"{job.get('title','')} {job.get('description','')} {job.get('required_skills','')}".lower()
    if any(kw in text for kw in ["zapier", "zap "]):
        return "zapier"
    if any(kw in text for kw in ["make.com", "make ", "integromat"]):
        return "make"
    if "n8n" in text:
        return "n8n"
    if any(kw in text for kw in ["hubspot", "salesforce", "crm", "pipedrive"]):
        return "crm"
    if any(kw in text for kw in ["scraping", "scraper", "crawl"]):
        return "scraping"
    if any(kw in text for kw in ["openai", "gpt", "claude", "llm", "langchain", "rag", "ai agent"]):
        return "ai"
    if any(kw in text for kw in ["api", "integration", "webhook", "rest"]):
        return "api"
    if any(kw in text for kw in ["discord", "slack", "telegram", "bot"]):
        return "bot"
    return "general"


def get_case_study(job_type: str) -> str:
    """Return the most relevant case study proof line."""
    case_studies = {
        "zapier": "Built this exact flow for a UK e-commerce brand: Shopify order → Google Sheets + Slack alert + Trello card. Zero failed triggers in 3 months.",
        "make": "Set up a Make.com scenario for a B2B SaaS: Typeform submission → HubSpot contact + Slack lead alert + automated follow-up sequence. 200+ leads processed daily without a single drop.",
        "n8n": "Built a Pipedrive webhook router in n8n for a client who'd outgrown Zapier's execution limits. Self-hosted on their VPS, fires in under 2 seconds, no usage caps.",
        "crm": "Connected Pipedrive to Google Sheets and Slack for a sales team — deal stage changes trigger instant notifications with deal value and next action. Their team stopped missing follow-ups.",
        "scraping": "Built scrapers for clients who needed competitor pricing data and lead enrichment. Playwright-based, handles anti-bot measures, outputs clean structured data on schedule.",
        "ai": "Integrated Claude API into a client's internal tool for document summarisation — context-aware, handles edge cases, falls back gracefully when the model is uncertain.",
        "api": "Connected HubSpot to a custom internal system via REST API — bidirectional sync, handles rate limits, logs every failed call for retry.",
        "bot": "Built a Telegram bot for a team's internal workflow — handles commands, manages state across conversations, connects to their database for real-time data.",
        "general": "Built similar automations for clients across e-commerce, SaaS, and professional services. Clean code, full docs, and a test run before handoff.",
    }
    return case_studies.get(job_type, case_studies["general"])


def get_opening(job: dict, job_type: str) -> str:
    """Generate a specific opening that references their actual problem."""
    title = job.get("title", "")
    desc = job.get("description", "")[:200]

    openings = {
        "zapier": f"Your {title.lower().replace('zapier ', '').replace('automation', 'automation').strip()} is a standard Zapier setup — I can have this live today.",
        "make": f"The Make.com scenario you're describing is exactly the kind of multi-step workflow I've built before. Self-contained, easy to maintain.",
        "n8n": f"n8n is the right tool here — self-hosted means no execution limits, and the workflow you need is well within its native capabilities.",
        "crm": f"CRM integrations are where I spend most of my time. The setup you need is achievable without custom code — clean and maintainable.",
        "scraping": f"The scraping setup you need is achievable — I can handle dynamic content, anti-bot measures, and output in whatever format you need.",
        "ai": f"AI integration that actually works in production requires more than just an API call. Context handling, fallbacks, edge cases — I build all of it.",
        "api": f"This is a clean API integration job — I've done dozens of these and know exactly where the friction points are.",
        "bot": f"The bot you're describing is a well-defined scope. I can have a working version in front of you within 48 hours.",
    }
    return openings.get(job_type, f"I read through your requirements carefully. This is a clean, well-defined project — here's how I'd approach it.")


def get_solution_bullets(job: dict, job_type: str) -> list[str]:
    """Return 3 specific solution bullets for this job type."""
    bullets = {
        "zapier": [
            "Set up Zap with correct trigger and action mapping to your spec",
            "Add error handling and test with 5 live events before handoff",
            "Loom walkthrough so you can edit it yourself if anything changes",
        ],
        "make": [
            "Build the scenario with data mapping to your exact field structure",
            "Add error handling and test with real data from your account",
            "Documentation covering every module and what it does",
        ],
        "n8n": [
            "Configure workflow with proper trigger, all nodes, and error handling",
            "Test against edge cases (empty data, API failures, retries)",
            "Deployment guide if you're self-hosting, or cloud setup if not",
        ],
        "crm": [
            "Map your data fields before touching anything in the live CRM",
            "Build automation with test data first, then migrate to production",
            "Document every trigger, action, and exception path",
        ],
        "scraping": [
            "Assess target site complexity, build scraper with appropriate method",
            "Handle pagination, dynamic content, and anti-bot if needed",
            "Structured output in your format + scheduler if recurring",
        ],
        "ai": [
            "Design the prompt pipeline with context management and fallbacks",
            "Build with confidence thresholds and graceful degradation",
            "Evaluation test set to validate output quality before you go live",
        ],
        "api": [
            "Spec the integration (endpoints, auth, data mapping) before writing code",
            "Build with retry logic, rate limiting, and error logging",
            "Test suite covering happy path and failure modes",
        ],
        "bot": [
            "Build core command handlers and state management",
            "Add error handling and logging so you can diagnose issues",
            "README with how to extend it yourself",
        ],
        "general": [
            "Clarify exact requirements and acceptance criteria before starting",
            "Build iteratively with updates at each milestone",
            "Deliver with full documentation and test evidence",
        ],
    }
    return bullets.get(job_type, bullets["general"])


def get_cta(job: dict, job_type: str) -> str:
    """Return a specific, low-friction CTA."""
    ctas = {
        "zapier": "One question: should this trigger on all events, or just a specific subset? (Takes 30 seconds to answer, saves back-and-forth.)",
        "make": "Quick question before I start: do you already have a Make.com account, or do I need to factor setup into the timeline?",
        "n8n": "Already have n8n running, or do you need the hosting sorted too?",
        "crm": "Happy to start with a scope doc (10-minute read) so we're aligned before touching your live data — want me to send one?",
        "scraping": "How often does this need to run, and what format do you need the output in? (Helps me quote accurately.)",
        "ai": "What's the failure mode you're most worried about? Helps me design the fallback correctly.",
        "api": "Do you have API documentation for both systems, or do I need to reverse-engineer one of them?",
        "bot": "What platform is this bot for, and do you have an existing account I can add it to?",
        "general": "Happy to send a quick scope breakdown first — 5 minutes to confirm, then I can start.",
    }
    return ctas.get(job_type, ctas["general"])


def generate_proposal(job: dict) -> tuple[str, float]:
    """Generate proposal text. Returns (text, confidence_pct)."""
    from pipeline.scoring import score_job_dict
    score_data = score_job_dict(job)
    ev = score_data["ev"]
    skill = score_data["skill_score"]

    job_type = detect_job_type(job)
    opening = get_opening(job, job_type)
    case_study = get_case_study(job_type)
    bullets = get_solution_bullets(job, job_type)
    cta = get_cta(job, job_type)

    budget = job.get("budget") or f"£{job.get('budget_min','?')}–{job.get('budget_max','?')}"
    skills = job.get("required_skills", job.get("skills", ""))

    proposal = f"""{opening}

Here's what I'd deliver:
- {bullets[0]}
- {bullets[1]}
- {bullets[2]}

{case_study}

{cta}

---
*EV: {ev:.0f} | Skill: {skill:.0f}% | Budget: {budget} | Skills: {skills[:60]}*
"""

    # Slop check
    slop_found = [p for p in SLOP_PATTERNS if p in proposal.lower()]
    if slop_found:
        print(f"  ⚠️  SLOP DETECTED: {slop_found}", file=sys.stderr)

    # Confidence
    confidence = round(min(90, (ev * 0.6) + (skill * 0.3) + (10 if not slop_found else 0)), 1)

    return proposal, confidence


def send_approval_request(job: dict, proposal: str, confidence: float, bot_token: str, chat_id: str) -> None:
    title = job["title"][:60]
    competition = job.get("proposals_count", 0)
    budget = job.get("budget") or f"£{job.get('budget_min','?')}"
    ev_data = {"ev": 0}
    try:
        from pipeline.scoring import score_job_dict
        ev_data = score_job_dict(job)
    except Exception:
        pass

    snipe = "🔴 SNIPE — FAST" if competition <= 5 else "📋 REVIEW"

    header = (
        f"{snipe}\n\n"
        f"*{title}*\n"
        f"EV: {ev_data.get('ev',0):.0f} | Budget: {budget} | {competition} competing proposals\n"
        f"Confidence: {confidence:.0f}%\n\n"
    )

    full_msg = header + "---\n\n" + proposal + "\n\n---\n\n✅ APPROVE | ✏️ EDIT | ❌ REJECT"

    # Split if too long
    if len(full_msg) > 4000:
        full_msg = full_msg[:3900] + "\n\n[truncated] ✅ APPROVE | ✏️ EDIT | ❌ REJECT"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": full_msg,
        "parse_mode": "Markdown",
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"  [WORDSMITH] telegram error: {e}", file=sys.stderr)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Generate proposal for a job")
    parser.add_argument("--job-id", help="Job ID from jobs.json/jobs.db")
    parser.add_argument("--json", help="Job data as JSON string")
    parser.add_argument("--notify", action="store_true", help="Send to Telegram for approval")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.json:
        job = json.loads(args.json)
    elif args.job_id:
        from pipeline.db import get_connection, apply_migrations
        conn = get_connection()
        apply_migrations(conn)
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (args.job_id,)).fetchone()
        if not row:
            print(f"Job not found: {args.job_id}")
            return 1
        job = dict(row)
        conn.close()
    else:
        print("Provide --job-id or --json")
        return 1

    proposal_text, confidence = generate_proposal(job)

    print(f"\nProposal for: {job.get('title','?')[:60]}")
    print(f"Confidence: {confidence:.0f}%")
    print("=" * 60)
    print(proposal_text)
    print("=" * 60)

    if args.notify and not args.dry_run:
        env = {}
        env_file = ROOT / "secrets" / "viper.env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
        bot_token = env.get("WORDSMITH_BOT_TOKEN", "")
        chat_id = env.get("WORDSMITH_CHAT_ID", "")
        send_approval_request(job, proposal_text, confidence, bot_token, chat_id)
        print("Sent to Telegram for approval")

        # Save to pending
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        safe_id = job.get("id", "unknown").replace("/", "_").replace(":", "_")
        out = PENDING_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_{safe_id}.md"
        out.write_text(proposal_text)
        print(f"Saved: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

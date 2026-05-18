"""EV-based job scoring model."""
from __future__ import annotations
import re

MY_SKILLS: dict[str, int] = {
    "python": 85, "api": 85, "api integration": 85, "automation": 85,
    "web scraping": 80, "scraping": 80, "beautifulsoup": 80, "selenium": 80,
    "openai": 80, "claude": 80, "gpt": 80, "ai": 75,
    "javascript": 80, "node.js": 80, "nodejs": 80,
    "webhooks": 75, "rest": 75, "integration": 75,
    "zapier": 70, "workflow": 70, "database": 75, "sql": 75,
    "data": 70, "etl": 70, "pandas": 75,
    "chatbot": 75, "bot": 75, "discord": 70, "slack": 70, "telegram": 75,
    "stripe": 75, "payment": 70,
    "langchain": 60, "rag": 65, "vector": 65,
    "make": 50, "make.com": 50, "integromat": 50,
    "n8n": 40, "n8n workflow": 40,
    "crm": 50, "hubspot": 35, "salesforce": 40, "zoho": 40, "pipedrive": 45,
    "gohighlevel": 20, "ghl": 20,
    "whatsapp": 40, "twilio": 40,
    "voice agent": 30, "vapi": 30, "retell": 30, "elevenlabs": 35,
    "airtable": 60, "notion": 60, "google sheets": 70,
    "marketing automation": 55, "email marketing": 55, "mailchimp": 55,
    "shopify": 55, "woocommerce": 50,
}

RED_FLAG_PATTERNS = [
    r"\bcheapest\b", r"\blowest\s+price\b", r"\bsimple\s+task\b",
    r"\bquick\s+fix\b", r"\bequity\s+only\b", r"\brevenue\s+share\s+only\b",
    r"\basap\b.*\b24\s*hours?\b",
]


def _skill_score(required_skills: str) -> float:
    if not required_skills:
        return 60.0
    skills = [s.strip().lower() for s in re.split(r"[,;/]", required_skills)]
    if not skills:
        return 60.0
    total = sum(MY_SKILLS.get(s, 30) for s in skills)
    return round(min(100.0, total / len(skills)), 1)


def _client_spend_value(spent_str: str) -> float:
    if not spent_str:
        return 0
    spent_str = spent_str.replace(",", "").replace("$", "").replace("£", "").upper()
    m = re.search(r"([\d.]+)\s*([KMB]?)\+?", spent_str)
    if not m:
        return 0
    val = float(m.group(1))
    suffix = m.group(2)
    return val * {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)


def _has_red_flags(job: dict) -> bool:
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    return any(re.search(p, text) for p in RED_FLAG_PATTERNS)


def score_job_dict(job: dict) -> dict:
    skill = _skill_score(job.get("required_skills", job.get("skills", "")))
    competition = int(job.get("proposals_count") or 0)
    budget_min = float(job.get("budget_min") or 0)
    client_spend = _client_spend_value(job.get("client_spent", ""))
    client_rating = float(job.get("client_rating") or 0)
    client_verified = bool(job.get("client_verified") or client_spend > 0)

    win_probability = max(10.0, 95.0 - min(80.0, competition * 1.2))
    speed_score = 90.0 if competition <= 10 else 65.0 if competition <= 30 else 40.0
    job_score = round((skill * 0.7) + (win_probability * 0.3), 1)
    ev = round((0.5 * job_score) + (0.3 * win_probability) + (0.2 * speed_score), 1)

    budget_bonus = 0.0
    if budget_min >= 2000:
        budget_bonus = 5.0
    elif budget_min >= 500:
        budget_bonus = 2.0

    quality_bonus = 0.0
    if client_spend >= 10000:
        quality_bonus += 3.0
    if client_rating >= 4.8:
        quality_bonus += 2.0
    if client_verified:
        quality_bonus += 1.0

    ev = round(min(100.0, ev + budget_bonus + quality_bonus), 1)

    return {
        "skill_score": skill,
        "job_score": job_score,
        "win_probability": win_probability,
        "speed_score": speed_score,
        "ev": ev,
        "red_flags": _has_red_flags(job),
    }


def score_root(job: dict) -> tuple[float, dict]:
    """Legacy root scorer (4-component weighted, 100pt max)."""
    budget = float(job.get("budget_min") or job.get("budget_max") or 0)
    skills_raw = job.get("required_skills", job.get("skills", ""))
    competition = int(job.get("proposals_count") or 0)
    client_spend = _client_spend_value(job.get("client_spent", ""))
    client_verified = bool(job.get("client_verified"))

    budget_score = 30 if budget >= 1000 else 20 if budget >= 500 else 10 if budget >= 200 else 0
    skill_pct = _skill_score(skills_raw)
    skills_score = round(skill_pct * 0.4, 1)
    comp_score = 15 if competition < 5 else 10 if competition < 10 else 5 if competition < 20 else 0
    client_score = 0
    if client_verified:
        client_score += 5
    if client_spend > 10000:
        client_score += 10
    elif client_spend > 1000:
        client_score += 5

    total = budget_score + skills_score + comp_score + client_score
    breakdown = {
        "budget": budget_score,
        "skills": skills_score,
        "competition": comp_score,
        "client_quality": client_score,
    }
    return round(total, 1), breakdown

"""Proposal generation — builds tailored proposal text from job data + score."""
from __future__ import annotations
import re
from .scoring import MY_SKILLS, _skill_score

SKILL_VARIANTS = {
    "n8n": "n8n (self-hosted, unlimited executions, no usage caps)",
    "zapier": "Zapier (rapid deployment, 5,000+ app ecosystem)",
    "make": "Make.com (visual multi-step automation, great for complex data flows)",
    "make.com": "Make.com (visual multi-step automation, great for complex data flows)",
    "hubspot": "HubSpot CRM automation",
    "salesforce": "Salesforce workflow and integration",
    "langchain": "LangChain + RAG (production-grade AI pipelines)",
    "rag": "RAG systems with semantic search and vector stores",
    "vapi": "Vapi/Retell voice AI agents",
    "whatsapp": "WhatsApp Business API automation",
    "stripe": "Stripe payment integration",
}

OPENING_TEMPLATES = {
    "n8n": "I build n8n workflows rather than defaulting to Zapier — that means self-hosted, infinitely customizable, and no execution caps hitting your automation at scale.",
    "ai": "AI automation is my core focus — I build agents and integrations that work reliably in production, not just demos. Context handling, fallbacks, human escalation paths: all included.",
    "chatbot": "I build chatbots that actually work past the demo stage — with proper session handling, fallback logic, and escalation paths to human agents.",
    "api": "API integrations are my bread and butter. I've connected dozens of systems and know exactly where the gotchas are — rate limits, auth edge cases, data type mismatches.",
    "crm": "CRM automation that actually gets adopted: clean data flows, sensible triggers, and documentation your team can understand and maintain.",
    "scraping": "Web scraping is something I've done at scale — anti-bot handling, rate limiting, dynamic content via Playwright, output in whatever format you need.",
    "default": "I read your spec carefully and I've built this exact type of system before. Here's how I'd approach it.",
}


def _detect_job_type(title: str, description: str, skills: str) -> str:
    text = f"{title} {description} {skills}".lower()
    for kw, jtype in [
        ("n8n", "n8n"), ("chatbot", "chatbot"), ("chat bot", "chatbot"),
        ("ai agent", "ai"), ("openai", "ai"), ("gpt", "ai"), ("claude", "ai"),
        ("langchain", "ai"), ("rag", "ai"),
        ("hubspot", "crm"), ("salesforce", "crm"), ("zoho", "crm"), ("crm", "crm"),
        ("scraping", "scraping"), ("scraper", "scraping"),
        ("api", "api"), ("integration", "api"), ("webhook", "api"),
    ]:
        if kw in text:
            return jtype
    return "default"


def _opening(job: dict) -> str:
    jtype = _detect_job_type(
        job.get("title", ""), job.get("description", ""), job.get("skills", "")
    )
    return OPENING_TEMPLATES.get(jtype, OPENING_TEMPLATES["default"])


def _proof_line(skills_str: str) -> str:
    skills = [s.strip().lower() for s in re.split(r"[,;/]", skills_str)]
    for s in skills:
        if s in SKILL_VARIANTS:
            return f"I've shipped multiple projects using {SKILL_VARIANTS[s]}."
    strong = [s for s in skills if MY_SKILLS.get(s, 0) >= 75]
    if strong:
        return f"I have strong production experience with {', '.join(strong[:3])}."
    return "I have relevant experience and can share examples on request."


def _solution_bullets(job: dict) -> str:
    jtype = _detect_job_type(
        job.get("title", ""), job.get("description", ""), job.get("skills", "")
    )
    bullets = {
        "n8n": [
            "Map your current process → identify every manual step to eliminate",
            "Build n8n workflow with error handling, retries, and alerting",
            "Test against edge cases, then document for your team",
        ],
        "api": [
            "Spec the integration contract (endpoints, auth, data mapping)",
            "Build with error handling, retries, and webhook validation",
            "Full test suite + runbook so you can maintain it yourself",
        ],
        "chatbot": [
            "Define conversation flows and fallback paths",
            "Build bot with context memory, escalation to human, rate limiting",
            "End-to-end testing + documentation of all training intents",
        ],
        "ai": [
            "Design AI pipeline (model choice, context window, chunking strategy)",
            "Build with proper error handling and confidence thresholds",
            "Evaluation suite to validate output quality before go-live",
        ],
        "crm": [
            "Audit your current CRM setup and data model",
            "Build automations with test data before touching live records",
            "Document every trigger, action, and exception path",
        ],
        "scraping": [
            "Identify data sources, assess anti-bot complexity",
            "Build resilient scraper (Playwright/requests, rotating headers, retry logic)",
            "Structured output in your preferred format + scheduling",
        ],
        "default": [
            "Clarify exact scope and acceptance criteria before writing a line of code",
            "Build iteratively with check-ins at each milestone",
            "Deliver with full docs and a working test suite",
        ],
    }
    items = bullets.get(jtype, bullets["default"])
    return "\n".join(f"- **{b.split('→')[0].strip()}**{' → ' + b.split('→')[1].strip() if '→' in b else ''}" for b in items)


def _confidence_from_score(score_data: dict, job: dict) -> float:
    ev = score_data.get("ev", 0)
    skill = score_data.get("skill_score", 0)
    competition = int(job.get("proposals_count") or 0)
    confidence = ev * 0.6 + skill * 0.3
    if competition < 5:
        confidence += 8
    elif competition > 50:
        confidence -= 10
    if skill < 50:
        confidence -= 15
    return round(min(95.0, max(30.0, confidence)), 1)


def build_human_proposal(job: dict, score_data: dict) -> tuple[str, float]:
    """Build a complete proposal. Returns (text, confidence_pct)."""
    title = job.get("title", "this project")
    budget = job.get("budget", job.get("budget_min", ""))
    skills = job.get("skills", job.get("required_skills", ""))
    competition = int(job.get("proposals_count") or 0)
    client_spent = job.get("client_spent", "")
    ev = score_data.get("ev", 0)
    confidence = _confidence_from_score(score_data, job)

    opening = _opening(job)
    solution = _solution_bullets(job)
    proof = _proof_line(skills)

    text = f"""# Proposal: {title}

**EV Score:** {ev:.1f} | **Confidence:** {confidence:.0f}% | **Competing proposals:** {competition}

---

{opening}

## What I'll deliver

{solution}

## Why this will work

{proof} Every deliverable comes with documentation and a test report — not just "it works on my machine."

## Next step

Happy to jump on a 15-min call to align on scope, or I can send a more detailed breakdown first — whichever works for you.

---

*Client: {client_spent} spent | Budget: {budget} | Skills required: {skills}*
"""
    return text, confidence

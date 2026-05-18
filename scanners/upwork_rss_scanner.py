#!/usr/bin/env python3
"""RSS-based Upwork job scanner — low platform risk, no login required.

Reads Upwork RSS feeds, normalizes to pipeline format, writes to data/jobs.json.
Run: python3 scanners/upwork_rss_scanner.py
"""
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "jobs.json"

RSS_FEEDS = [
    "https://www.upwork.com/ab/feed/jobs/rss?q=zapier+automation&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=api+integration&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=n8n+workflow&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=web+scraping+python&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=chatbot+automation&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=make+automation&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=discord+bot&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=openai+integration&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=google+sheets+automation&sort=recency&api_params=1",
    "https://www.upwork.com/ab/feed/jobs/rss?q=workflow+automation&sort=recency&api_params=1",
]

SKILL_KEYWORDS = [
    "python", "n8n", "zapier", "make", "api", "integration", "automation",
    "chatbot", "bot", "discord", "slack", "telegram", "openai", "gpt",
    "langchain", "rag", "hubspot", "salesforce", "crm", "airtable", "notion",
    "webhook", "scraping", "selenium", "playwright", "javascript", "node",
]


def _extract_skills(text: str) -> str:
    text_lower = text.lower()
    found = [kw for kw in SKILL_KEYWORDS if kw in text_lower]
    return ", ".join(dict.fromkeys(found))


def _parse_budget(text: str) -> tuple:
    m = re.search(r'\$([0-9,]+)[\s\-–]+\$([0-9,]+)', text or "")
    if m:
        return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
    m = re.search(r'\$([0-9,]+)', text or "")
    if m:
        v = float(m.group(1).replace(",", ""))
        return v, v
    return None, None


def _job_id(url: str) -> str:
    return "upwork_rss_" + hashlib.md5(url.encode()).hexdigest()[:16]


def fetch_feed(url: str) -> list[dict]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            xml = r.read()
        root = ET.fromstring(xml)
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
        items = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            content = (item.findtext("content:encoded", namespaces=ns) or "").strip()
            full_text = f"{title} {desc} {content}"
            full_text_clean = re.sub(r"<[^>]+>", " ", full_text)
            budget_min, budget_max = _parse_budget(full_text_clean)
            skills = _extract_skills(full_text_clean)
            items.append({
                "id": _job_id(link),
                "platform": "upwork",
                "title": title,
                "description": re.sub(r"<[^>]+>", " ", desc)[:600].strip(),
                "url": link,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "budget_type": "fixed",
                "required_skills": skills,
                "proposals_count": 0,
                "client_rating": None,
                "client_spent": None,
                "status": "discovered",
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            })
        return items
    except Exception as e:
        print(f"  [RSS] error fetching {url[:60]}: {e}", file=sys.stderr)
        return []


def main() -> int:
    print(f"[RSS SCANNER] {datetime.now(timezone.utc).isoformat()}")
    seen: set[str] = set()
    jobs: list[dict] = []

    existing = []
    if OUT.exists():
        try:
            data = json.loads(OUT.read_text())
            existing = data.get("jobs", []) if isinstance(data, dict) else data
            seen = {j["id"] for j in existing if j.get("id")}
        except Exception:
            pass

    for feed_url in RSS_FEEDS:
        print(f"  fetching: {feed_url[50:90]}")
        items = fetch_feed(feed_url)
        new = [j for j in items if j["id"] not in seen]
        for j in new:
            seen.add(j["id"])
            jobs.append(j)

    all_jobs = jobs + existing
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"jobs": all_jobs, "updated": datetime.now(timezone.utc).isoformat(), "total": len(all_jobs)}, indent=2),
        encoding="utf-8",
    )
    print(f"[RSS SCANNER] done: {len(jobs)} new jobs, {len(all_jobs)} total in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

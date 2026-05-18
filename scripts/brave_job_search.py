#!/usr/bin/env python3
"""
Upwork Job Scanner — uses Brave Search API to find live Upwork job listings.
Writes fresh jobs to data/jobs.json for pipeline ingestion.
Run: python3 scripts/brave_job_search.py
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'jobs.json'

BRAVE_API_KEY = os.getenv('BRAVE_API_KEY', '')
BRAVE_ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'

QUERIES = [
    'site:upwork.com "zapier automation" OR "make automation" posted:day',
    'site:upwork.com "n8n workflow" OR "api integration" posted:day',
    'site:upwork.com "discord bot" OR "slack bot" OR "webhook" posted:day',
    'site:upwork.com "web scraping" OR "python automation" posted:day',
    'site:upwork.com "openai integration" OR "chatgpt" OR "ai chatbot" posted:day',
    'site:upwork.com "ai agent" OR "langchain" OR "rag" posted:day',
    'site:upwork.com "airtable" OR "notion api" OR "hubspot integration" posted:day',
    'site:upwork.com "workflow automation" budget posted:day',
]

POSITIVE_KW = [
    'automation', 'chatbot', 'api', 'integration', 'bot', 'scraping',
    'python', 'node', 'javascript', 'openai', 'gpt', 'claude', 'n8n',
    'zapier', 'make', 'webhook', 'airtable', 'notion', 'hubspot', 'crm',
    'slack', 'discord', 'langchain', 'rag', 'workflow',
]
NEGATIVE_KW = [
    'mobile app', 'ios', 'android', 'react native', 'flutter', 'unity',
    'game', '3d', 'blockchain', 'solidity', 'machine learning training',
    'on-site', 'full-time employee',
]


def brave_search(query: str, count: int = 10) -> list[dict]:
    if not BRAVE_API_KEY:
        print("ERROR: BRAVE_API_KEY not set", file=sys.stderr)
        return []
    params = urllib.parse.urlencode({'q': query, 'count': count, 'freshness': 'pd'})
    req = urllib.request.Request(
        f"{BRAVE_ENDPOINT}?{params}",
        headers={
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': BRAVE_API_KEY,
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            import gzip
            raw = r.read()
            if r.info().get('Content-Encoding') == 'gzip':
                raw = gzip.decompress(raw)
            return json.loads(raw).get('web', {}).get('results', [])
    except Exception as e:
        print(f"  brave error: {e}", file=sys.stderr)
        return []


def parse_budget(text: str) -> tuple:
    fixed = re.search(r'\$([0-9,]+)', text or '')
    hourly = re.search(r'\$([0-9.]+)[^0-9]+\$([0-9.]+)\s*/hr', text or '')
    if hourly:
        return float(hourly.group(1)), float(hourly.group(2))
    if fixed:
        v = float(fixed.group(1).replace(',', ''))
        return v, v
    return None, None


def quick_score(title: str, desc: str, budget_max: float) -> int:
    text = (title + ' ' + desc).lower()
    score = 0
    for kw in POSITIVE_KW:
        if kw in text:
            score += 5
    for kw in NEGATIVE_KW:
        if kw in text:
            score -= 15
    if budget_max:
        if budget_max > 1000: score += 30
        elif budget_max > 500: score += 20
        elif budget_max > 200: score += 10
    return max(0, score)


def result_to_job(r: dict) -> dict | None:
    url = r.get('url', '')
    if 'upwork.com' not in url:
        return None
    title = r.get('title', '').strip()
    desc = r.get('description', '').strip()
    if not title:
        return None
    uid = re.sub(r'[^a-zA-Z0-9]', '_', title[:40]) + '_' + str(hash(url))[-6:]
    bmin, bmax = parse_budget(desc)
    score = quick_score(title, desc, bmax or 0)
    return {
        'id': uid,
        'platform': 'upwork',
        'title': title,
        'description': desc[:600],
        'url': url,
        'posted': datetime.now(timezone.utc).isoformat(),
        'budget_min': bmin,
        'budget_max': bmax,
        'proposals_count': 0,
        'required_skills': '',
        'client_rating': None,
        'client_spend': None,
        'status': 'discovered',
        'quick_score': score,
    }


def scan() -> list[dict]:
    seen: set[str] = set()
    jobs: list[dict] = []
    for query in QUERIES:
        print(f"  searching: {query[:60]}")
        results = brave_search(query, count=10)
        for r in results:
            job = result_to_job(r)
            if not job or job['id'] in seen:
                continue
            seen.add(job['id'])
            jobs.append(job)
        time.sleep(0.3)
    jobs.sort(key=lambda j: j['quick_score'], reverse=True)
    return jobs


def main():
    if not BRAVE_API_KEY:
        print("ERROR: Set BRAVE_API_KEY env variable", file=sys.stderr)
        sys.exit(1)
    print(f"[SCANNER] {datetime.now(timezone.utc).isoformat()} starting Brave Search scan")
    jobs = scan()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'jobs': jobs, 'updated': datetime.now(timezone.utc).isoformat(), 'total': len(jobs)}, indent=2), encoding='utf-8')
    print(f"[SCANNER] done: {len(jobs)} jobs written to {OUT}")
    top = [j for j in jobs if j['quick_score'] >= 40]
    print(f"[SCANNER] high-score (>=40): {len(top)}")
    for j in top[:5]:
        print(f"  [{j['quick_score']}] {j['title'][:70]}")


if __name__ == '__main__':
    main()

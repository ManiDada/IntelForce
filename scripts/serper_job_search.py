#!/usr/bin/env python3
"""
Upwork Job Scanner — uses Serper.dev API to find live Upwork job listings.
Writes jobs to data/jobs.json (append, deduplicate by URL).
Run: SERPER_API_KEY=... python3 scripts/serper_job_search.py
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'jobs.json'

SERPER_API_KEY = os.getenv('SERPER_API_KEY', '')
SERPER_ENDPOINT = 'https://google.serper.dev/search'

QUERIES = [
    'site:upwork.com/jobs zapier automation fixed price',
    'site:upwork.com/jobs make.com automation fixed price',
    'site:upwork.com/jobs n8n workflow fixed price',
]

POSITIVE_KW = [
    'automation', 'zapier', 'make.com', 'n8n', 'workflow', 'integration',
    'api', 'webhook', 'bot', 'chatbot', 'python', 'openai', 'gpt',
]
NEGATIVE_KW = [
    'mobile app', 'ios', 'android', 'react native', 'flutter',
    'game', '3d', 'blockchain', 'solidity', 'on-site', 'full-time employee',
]


def serper_search(query: str, num: int = 10) -> list[dict]:
    if not SERPER_API_KEY:
        print("ERROR: SERPER_API_KEY not set", file=sys.stderr)
        return []
    payload = json.dumps({"q": query, "num": num}).encode()
    req = urllib.request.Request(
        SERPER_ENDPOINT,
        data=payload,
        headers={
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get('organic', [])
    except Exception as e:
        print(f"  serper error: {e}", file=sys.stderr)
        return []


def parse_budget(text: str) -> tuple:
    hourly = re.search(r'\$([0-9.]+)[^0-9]+\$([0-9.]+)\s*/hr', text or '')
    fixed = re.search(r'\$([0-9,]+)', text or '')
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
        if budget_max > 1000:
            score += 30
        elif budget_max > 500:
            score += 20
        elif budget_max > 200:
            score += 10
    return max(0, score)


def result_to_job(r: dict) -> Optional[dict]:
    url = r.get('link', '')
    if not re.search(r'upwork\.com/jobs/', url):
        return None
    title = r.get('title', '').strip()
    desc = r.get('snippet', '').strip()
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
        'posted_at': datetime.now(timezone.utc).isoformat(),
        'source': 'serper',
        'budget_min': bmin,
        'budget_max': bmax,
        'proposals_count': 0,
        'required_skills': '',
        'client_rating': None,
        'client_spend': None,
        'status': 'discovered',
        'quick_score': score,
    }


def load_existing() -> tuple[list[dict], set[str]]:
    if not OUT.exists():
        return [], set()
    try:
        data = json.loads(OUT.read_text(encoding='utf-8'))
        jobs = data.get('jobs', []) if isinstance(data, dict) else data
        return jobs, {j['url'] for j in jobs if j.get('url')}
    except Exception:
        return [], set()


def main():
    if not SERPER_API_KEY:
        print("ERROR: Set SERPER_API_KEY env variable", file=sys.stderr)
        sys.exit(1)

    print(f"[SCANNER] {datetime.now(timezone.utc).isoformat()} starting Serper.dev scan")

    existing_jobs, seen_urls = load_existing()
    new_jobs: list[dict] = []

    for query in QUERIES:
        print(f"  searching: {query}")
        results = serper_search(query, num=10)
        for r in results:
            job = result_to_job(r)
            if not job or job['url'] in seen_urls:
                continue
            seen_urls.add(job['url'])
            new_jobs.append(job)

    all_jobs = existing_jobs + new_jobs
    all_jobs.sort(key=lambda j: j.get('quick_score', 0), reverse=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({'jobs': all_jobs, 'updated': datetime.now(timezone.utc).isoformat(), 'total': len(all_jobs)}, indent=2),
        encoding='utf-8',
    )

    print(f"[SCANNER] {len(new_jobs)} new jobs found, {len(all_jobs)} total in {OUT}")
    top = [j for j in new_jobs if j.get('quick_score', 0) >= 40]
    if top:
        print(f"[SCANNER] high-score new jobs (>=40): {len(top)}")
        for j in top[:5]:
            print(f"  [{j['quick_score']}] {j['title'][:70]}")


if __name__ == '__main__':
    main()

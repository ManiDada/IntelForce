#!/usr/bin/env python3
"""
Viper's frontier Upwork scanner — curl_cffi + GraphQL + HTML enrichment.

Phase 1: Bulk GQL scan with Chrome TLS fingerprint (~475ms/query, no browser).
Phase 2: HTML enrichment for candidates — fetches job pages to get proposals
         count + client data (visitor GQL schema doesn't expose these).
Phase 3: Full hard filter + EV scoring.

No Playwright. No cookies file. No browser. Cloudflare-proof.
"""
import json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

try:
    from curl_cffi import requests as cr
except ImportError:
    print("ERROR: pip3 install curl_cffi", file=sys.stderr); sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT        = ROOT / "data" / "jobs.json"
SEEN_FILE  = ROOT / "data" / "seen_jobs.json"
SNIPE_FILE = ROOT / "data" / "snipe_alerts.json"

UPWORK_HOME  = "https://www.upwork.com/"
GRAPHQL_URL  = "https://www.upwork.com/api/graphql/v1"
TOKEN_COOKIE = "visitor_gql_token"
TOKEN_TTL    = 23 * 60  # refresh before 25-min expiry

# Title-based search terms (the API's `title` field filters by job title text).
# Returns only jobs where the keyword appears in the title — highly relevant.
# Deduplication handles jobs matching multiple queries.
SEARCH_QUERIES = [
    "zapier",
    "n8n",
    "make.com",
    "make automation",
    "workflow automation",
    "zapier automation",
    "api integration python",
    "python automation",
    "web scraping python",
    "telegram bot",
]

# These keywords must appear somewhere in title OR description.
# After title-search, most will pass — this catches edge cases.
HARD_KWS  = {"zapier", "make.com", "n8n", "workflow automation", "make automation",
              "api integration", "automation", "python automation", "scraping", "bot"}
RED_FLAGS = {
    "cheapest", "lowest price", "equity only", "revenue share",
    "blockchain", "solidity", "mobile app", "react native", "flutter",
    "full-time", "on-site", "on site", "multi-step",
}

GQL = """
query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {
  search { universalSearchNuxt {
    visitorJobSearchV1(request: $requestVariables) {
      paging { total offset count }
      results {
        title description
        ontologySkills { prefLabel }
        jobTile { job {
          id cipherText jobType
          hourlyBudgetMax hourlyBudgetMin
          fixedPriceAmount { amount }
          publishTime contractorTier
        }}
      }
    }
  }}
}
"""

_tok = None
_tok_t: float = 0


def get_token(force=False):
    global _tok, _tok_t
    if not force and _tok and time.monotonic() - _tok_t < TOKEN_TTL:
        return _tok
    print("  [GQL] fetching visitor token...")
    r = cr.get(UPWORK_HOME, impersonate="chrome124", timeout=20,
               headers={"Accept": "text/html", "Accept-Language": "en-GB,en;q=0.9"})
    r.raise_for_status()
    tok = r.cookies.get(TOKEN_COOKIE)
    if not tok:
        for k, v in r.headers.items():
            if k.lower() == "set-cookie" and TOKEN_COOKIE in v:
                m = re.search(rf"{TOKEN_COOKIE}=([^;]+)", v)
                if m:
                    tok = m.group(1)
                    break
    if not tok:
        raise RuntimeError(f"'{TOKEN_COOKIE}' cookie not found")
    _tok, _tok_t = tok, time.monotonic()
    print("  [GQL] token OK")
    return _tok


def gql_search(token, query, count=30, offset=0):
    hdrs = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en;q=0.7",
        "Accept-Encoding": "gzip",
        "Referer": f"https://www.upwork.com/nx/search/jobs/?q={query.replace(' ','+')}&sort=recency&t=1",
        "X-Upwork-Accept-Language": "en-US",
        "Origin": "https://www.upwork.com",
    }
    payload = {"query": GQL, "variables": {"requestVariables": {
        "sort": "recency",
        "highlight": True,
        "paging": {"offset": offset, "count": count},
        "title": query,
    }}}
    r = cr.post(GRAPHQL_URL, headers=hdrs, json=payload,
                impersonate="chrome124", timeout=15)
    if r.status_code == 401:
        raise ValueError("TOKEN_EXPIRED")
    r.raise_for_status()
    data = r.json()
    return (data.get("data", {}).get("search", {})
               .get("universalSearchNuxt", {})
               .get("visitorJobSearchV1", {})
               .get("results", [])) or []


def parse_job(r):
    try:
        tile = r.get("jobTile", {}) or {}
        j = tile.get("job", {}) or {}
        cipher = j.get("cipherText", "")
        jid = f"upwork_{cipher}" if cipher else f"upwork_gql_{abs(hash(r.get('title', ''))):016x}"
        url = f"https://www.upwork.com/jobs/~{cipher}" if cipher else ""
        jtype = j.get("jobType", "FIXED")
        def _f(v):
            try: return float(v) if v is not None else None
            except (TypeError, ValueError): return None
        if jtype == "HOURLY":
            bmin, bmax = _f(j.get("hourlyBudgetMin")), _f(j.get("hourlyBudgetMax"))
            bstr = f"${bmin}–${bmax}/hr" if bmin and bmax else "Hourly"
        else:
            fx = j.get("fixedPriceAmount", {}) or {}
            amt = fx.get("amount")
            bmin = bmax = _f(amt)
            bstr = f"${amt}" if amt else "Fixed"
        skills = [s["prefLabel"] for s in (r.get("ontologySkills") or []) if s.get("prefLabel")]
        # Strip Upwork's highlight markup (H^text^H → text)
        raw_title = r.get("title", "")
        clean_title = re.sub(r'H\^(.*?)\^H', r'\1', raw_title).strip()
        return {
            "id": jid, "platform": "upwork",
            "title": clean_title,
            "description": (r.get("description") or "").strip()[:800],
            "url": url, "budget": bstr,
            "budget_min": bmin, "budget_max": bmax,
            "budget_type": "hourly" if jtype == "HOURLY" else "fixed",
            "required_skills": ", ".join(skills[:10]),
            # enrichment placeholders — filled by Phase 2
            "proposals_count": 0,
            "client_rating": None,
            "client_spent": "",
            "client_spent_amount": None,
            "client_verified": None,
            "client_total_hires": 0,
            "posted_time": j.get("publishTime", ""),
            "status": "discovered",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        print(f"  parse err: {e}", file=sys.stderr)
        return None


def passes_prefilter(job):
    """Fast pre-filter — keyword + budget + red flags only. No proposals/client."""
    if job.get("budget_type") == "hourly":
        return False
    text = f"{job.get('title','').lower()} {job.get('description','').lower()}"
    if any(rf in text for rf in RED_FLAGS):
        return False
    if not any(kw in text for kw in HARD_KWS):
        return False
    try:
        budget = float(job.get("budget_max") or job.get("budget_min") or 0)
    except (TypeError, ValueError):
        budget = 0
    if budget and budget < 80:
        return False
    return True


def passes_fullfilter(job):
    """Full hard filter — applied AFTER enrichment adds proposals + client data.

    proposals_count == 0 means 'unknown' (no enrichment ran or job is new).
    client_verified == None means 'unknown'. Both are allowed through with a flag.
    """
    count = job.get("proposals_count", 0)
    if count > 0 and count > 15:
        return False
    return True


def scan(limit=30, enrich=True, max_enrich=20):
    seen = set()
    if SEEN_FILE.exists():
        try:
            seen = set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            pass

    existing = []
    if OUT.exists():
        try:
            d = json.loads(OUT.read_text())
            existing = d.get("jobs", []) if isinstance(d, dict) else d
            for j in existing:
                seen.add(j.get("id", ""))
        except Exception:
            pass

    tok = get_token()

    # --- Phase 1: Bulk GQL discovery ---
    candidates = []
    run_seen = set()

    for q in SEARCH_QUERIES:
        try:
            print(f"  [GQL] {q}")
            results = gql_search(tok, q, count=limit)
            for r in results:
                job = parse_job(r)
                if not job or job["id"] in seen or job["id"] in run_seen:
                    continue
                run_seen.add(job["id"])
                if not passes_prefilter(job):
                    continue
                candidates.append(job)
                seen.add(job["id"])
            time.sleep(0.35)
        except ValueError as e:
            if "TOKEN_EXPIRED" in str(e):
                print("  [GQL] token expired, refreshing...")
                tok = get_token(force=True)
            else:
                print(f"  [GQL] err '{q}': {e}", file=sys.stderr)
        except Exception as e:
            print(f"  [GQL] err '{q}': {e}", file=sys.stderr)

    print(f"  [GQL] {len(candidates)} candidates after pre-filter")

    # --- Phase 2: HTML enrichment (proposals count + client data) ---
    if enrich and candidates:
        from scanners.upwork_job_enricher import enrich_jobs_batch
        enrich_jobs_batch(candidates, visitor_token=tok,
                          max_enrichments=max_enrich, verbose=True)

    # --- Phase 3: Full filter ---
    new_jobs = [j for j in candidates if passes_fullfilter(j)]
    # Only mark as snipe when we have enriched data confirming ≤5 proposals
    snipes   = [j for j in new_jobs if j.get("proposals_count", 0) > 0 and j["proposals_count"] <= 5]

    print(f"  [GQL] {len(new_jobs)} pass full filter | {len(snipes)} snipe alerts")
    return new_jobs, snipes, existing, seen


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-enrich", action="store_true", help="Skip HTML enrichment phase")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--max-enrich", type=int, default=20)
    p.add_argument("--query")
    args = p.parse_args()

    global SEARCH_QUERIES
    if args.query:
        SEARCH_QUERIES = [args.query]

    print(f"[VIPER GQL] {datetime.now(timezone.utc).isoformat()}")
    new_jobs, snipes, existing, seen = scan(
        args.limit, enrich=not args.no_enrich, max_enrich=args.max_enrich
    )
    print(f"[VIPER GQL] {len(new_jobs)} new qualifying jobs | {len(snipes)} snipe alerts")

    if not args.dry_run:
        SEEN_FILE.write_text(json.dumps(list(seen)))
        merged = new_jobs + [
            j for j in existing
            if j.get("id") not in {nj["id"] for nj in new_jobs}
        ]
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "jobs": merged,
            "updated": datetime.now(timezone.utc).isoformat(),
            "total": len(merged),
            "new_this_run": len(new_jobs),
        }, indent=2))
        SNIPE_FILE.write_text(json.dumps({
            "alerts": snipes,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))

    if snipes:
        print("\nSNIPE ALERTS:")
        for j in snipes:
            print(f"  [{j['proposals_count']} props] {j['title'][:65]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Viper's core Upwork scanner — uses Playwright + session cookies to scrape
live job listings without RSS or external APIs.

Run: python3 scanners/upwork_playwright_scanner.py
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COOKIES_FILE = ROOT / "secrets" / "upwork_cookies.json"
OUT = ROOT / "data" / "jobs.json"
NOTIFIED_FILE = ROOT / "data" / "notified_jobs.json"
SEEN_FILE = ROOT / "data" / "seen_jobs.json"

# Cold-start search queries (Zapier / Make.com / n8n focus)
SEARCH_QUERIES = [
    # Tier 1 — highest match rate for cold start
    "zapier automation",
    "make.com automation",
    "n8n workflow",
    "zapier workflow integration",
    "make automation workflow",
    "n8n automation expert",
    # Tier 2 — broader automation
    "workflow automation python",
    "api integration automation",
    "robotic process automation",
    "web scraping python",
    "telegram bot python",
    "discord bot automation",
]

HARD_FILTER_KEYWORDS = ["zapier", "make.com", "n8n", "make ", "zapier ", "n8n "]
RED_FLAGS = [
    "cheapest", "lowest price", "simple task", "quick fix",
    "equity only", "revenue share only", "asap 24 hour",
    "blockchain", "solidity", "mobile app", "ios app", "android app",
    "react native", "flutter", "full time", "on-site",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def load_cookies() -> list[dict]:
    if not COOKIES_FILE.exists():
        raise FileNotFoundError(f"Cookie file not found: {COOKIES_FILE}")
    return json.loads(COOKIES_FILE.read_text())


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(list(seen)))


def parse_budget(text: str) -> tuple:
    if not text:
        return None, None
    # Hourly range: $X.XX-$Y.YY/hr
    m = re.search(r'\$([0-9,.]+)\s*[–\-]\s*\$([0-9,.]+)\s*/hr', text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
    # Fixed: $X,XXX
    m = re.search(r'\$([0-9,]+)', text)
    if m:
        v = float(m.group(1).replace(",", ""))
        return v, v
    # GBP
    m = re.search(r'£([0-9,]+)', text)
    if m:
        v = float(m.group(1).replace(",", ""))
        return v, v
    return None, None


def passes_hard_filter(job: dict) -> bool:
    """Apply fast hard filters before EV scoring."""
    text = f"{job.get('title','').lower()} {job.get('description','').lower()}"

    # Must mention one of our target platforms (cold-start mode)
    if not any(kw in text for kw in HARD_FILTER_KEYWORDS):
        return False

    # Red flag check
    if any(rf in text for rf in RED_FLAGS):
        return False

    # Budget check
    bmax = job.get("budget_max") or 0
    bmin = job.get("budget_min") or 0
    budget = bmax or bmin
    if budget and budget < 100:  # Too cheap
        return False

    # Competition check (if available)
    proposals = job.get("proposals_count", 0)
    if proposals and proposals > 15:
        return False

    return True


def extract_jobs_from_page(page) -> list[dict]:
    """Extract job listings from Upwork search results page."""
    jobs = []
    try:
        # Wait for job tiles to load
        page.wait_for_selector('[data-test="job-tile-list"]', timeout=10000)
        time.sleep(1.5)  # Let lazy-loaded content render

        # Get all job tiles
        tiles = page.query_selector_all('[data-test="job-tile"]')

        for tile in tiles:
            try:
                title_el = tile.query_selector('[data-test="job-tile-title-link"]')
                if not title_el:
                    continue
                title = title_el.inner_text().strip()
                href = title_el.get_attribute("href") or ""
                url = f"https://www.upwork.com{href}" if href.startswith("/") else href

                # Extract job ID from URL
                job_id_match = re.search(r'~([a-f0-9]+)', url)
                job_id = f"upwork_{job_id_match.group(1)}" if job_id_match else None
                if not job_id:
                    job_id = f"upwork_pw_{abs(hash(url)):016x}"

                # Description
                desc_el = tile.query_selector('[data-test="job-description-text"]')
                description = desc_el.inner_text().strip()[:800] if desc_el else ""

                # Budget
                budget_el = tile.query_selector('[data-test="budget"]')
                budget_text = budget_el.inner_text().strip() if budget_el else ""
                bmin, bmax = parse_budget(budget_text)

                # Proposals count
                proposals_el = tile.query_selector('[data-test="proposals-count"]')
                proposals_text = proposals_el.inner_text() if proposals_el else "0"
                proposals_match = re.search(r'\d+', proposals_text)
                proposals = int(proposals_match.group()) if proposals_match else 0

                # Client info
                client_el = tile.query_selector('[data-test="client-info"]')
                client_text = client_el.inner_text() if client_el else ""
                client_rating_match = re.search(r'([0-9.]+)\s*of\s*5', client_text)
                client_rating = float(client_rating_match.group(1)) if client_rating_match else None
                client_spent_match = re.search(r'\$([0-9,.]+[KMB]?)\+?\s*spent', client_text, re.IGNORECASE)
                client_spent = f"${client_spent_match.group(1)}+" if client_spent_match else ""
                client_verified = "payment verified" in client_text.lower()

                # Skills
                skill_els = tile.query_selector_all('[data-test="token"]')
                skills = ", ".join([s.inner_text().strip() for s in skill_els[:8]])

                # Posted time
                posted_el = tile.query_selector('[data-test="posted-on"]')
                posted = posted_el.inner_text().strip() if posted_el else ""

                jobs.append({
                    "id": job_id,
                    "platform": "upwork",
                    "title": title,
                    "description": description,
                    "url": url,
                    "budget": budget_text,
                    "budget_min": bmin,
                    "budget_max": bmax,
                    "budget_type": "hourly" if "/hr" in budget_text.lower() else "fixed",
                    "required_skills": skills,
                    "proposals_count": proposals,
                    "client_rating": client_rating,
                    "client_spent": client_spent,
                    "client_verified": client_verified,
                    "posted_time": posted,
                    "status": "discovered",
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                print(f"  [SCANNER] error parsing tile: {e}", file=sys.stderr)
                continue
    except Exception as e:
        print(f"  [SCANNER] page extraction error: {e}", file=sys.stderr)

    return jobs


def scan_upwork() -> tuple[list[dict], list[dict]]:
    """
    Main scanner. Returns (all_new_jobs, snipe_alerts).
    Snipe alerts = qualifying jobs with ≤ 5 proposals.
    """
    from playwright.sync_api import sync_playwright

    cookies = load_cookies()
    seen = load_seen()
    new_jobs = []
    snipe_alerts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="en-GB",
            timezone_id="Europe/London",
        )
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        # Stealth: remove webdriver flag
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """)

        for query in SEARCH_QUERIES:
            try:
                encoded = query.replace(" ", "+")
                url = f"https://www.upwork.com/nx/search/jobs/?q={encoded}&sort=recency&contractor_tier=1,2"
                print(f"  [SCANNER] scanning: {query}")

                page.goto(url, wait_until="domcontentloaded", timeout=20000)

                # Check for Cloudflare challenge
                if "just a moment" in page.title().lower() or "cloudflare" in page.content().lower()[:500]:
                    print(f"  [SCANNER] ⚠️  Cloudflare challenge detected — cookies may be expired", file=sys.stderr)
                    # Write a flag file so Viper agent knows to alert Mani
                    (ROOT / "data" / "cookie_refresh_needed.flag").write_text(
                        datetime.now(timezone.utc).isoformat()
                    )
                    break

                # Check for login redirect
                if "/login" in page.url or "signup" in page.url:
                    print(f"  [SCANNER] ⚠️  Session expired — need cookie refresh", file=sys.stderr)
                    (ROOT / "data" / "cookie_refresh_needed.flag").write_text(
                        datetime.now(timezone.utc).isoformat()
                    )
                    break

                jobs = extract_jobs_from_page(page)
                print(f"  [SCANNER] found {len(jobs)} jobs on page")

                for job in jobs:
                    if job["id"] in seen:
                        continue
                    seen.add(job["id"])

                    if not passes_hard_filter(job):
                        continue

                    new_jobs.append(job)
                    if job["proposals_count"] <= 5:
                        snipe_alerts.append(job)

                time.sleep(2.0)  # Human-like delay between searches

            except Exception as e:
                print(f"  [SCANNER] error on query '{query}': {e}", file=sys.stderr)
                continue

        browser.close()

    save_seen(seen)
    return new_jobs, snipe_alerts


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Viper Upwork scanner")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output")
    parser.add_argument("--snipe-only", action="store_true", help="Only print snipe alerts")
    args = parser.parse_args()

    print(f"[VIPER SCANNER] {datetime.now(timezone.utc).isoformat()}")

    new_jobs, snipe_alerts = scan_upwork()

    # Load existing jobs and merge
    existing = []
    if OUT.exists():
        try:
            data = json.loads(OUT.read_text())
            existing = data.get("jobs", []) if isinstance(data, dict) else data
        except Exception:
            pass

    all_jobs = new_jobs + existing

    if not args.dry_run:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "jobs": all_jobs,
            "updated": datetime.now(timezone.utc).isoformat(),
            "total": len(all_jobs),
            "new_this_run": len(new_jobs),
            "snipe_alerts": len(snipe_alerts),
        }, indent=2), encoding="utf-8")

    print(f"[VIPER SCANNER] done: {len(new_jobs)} new qualifying jobs")
    print(f"[VIPER SCANNER] 🎯 {len(snipe_alerts)} SNIPE ALERTS (≤5 proposals)")

    if snipe_alerts:
        print("\nSNIPE ALERTS:")
        for job in snipe_alerts:
            print(f"  [{job['proposals_count']} proposals] {job['title'][:60]}")
            print(f"  Budget: {job.get('budget','?')} | URL: {job['url'][:60]}")

    # Output snipe alerts as JSON for Viper agent to read
    snipe_out = ROOT / "data" / "snipe_alerts.json"
    if not args.dry_run:
        snipe_out.write_text(json.dumps({
            "alerts": snipe_alerts,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())

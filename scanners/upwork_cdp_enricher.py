#!/usr/bin/env python3
"""
Chrome CDP job enricher — uses real Chrome via Patchright to fetch Upwork job
pages and extract proposals count + client data.

Works WITHOUT login for proposals count (visitor view exposes totalApplicants).
Client verification data requires login.

Run via: python3 -m scanners.upwork_cdp_enricher <cipher>
"""
import asyncio
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "upwork-mcp" / "src"))

PAGE_TIMEOUT = 20_000   # ms per page
RATE_LIMIT   = 0.5      # seconds between requests (Chrome handles rapid nav fine)
MAX_PAGES    = 3        # Patchright page pool size


def _is_cdp_running() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _start_chrome() -> bool:
    import subprocess
    from upwork_mcp.browser.client import find_chrome, PROFILE_DIR
    chrome = find_chrome()
    if not chrome:
        return False
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [chrome, "--remote-debugging-port=9222",
         f"--user-data-dir={PROFILE_DIR}",
         "--no-first-run", "--no-default-browser-check",
         "--disable-background-networking"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Poll until ready
    for _ in range(15):
        time.sleep(1)
        if _is_cdp_running():
            return True
    return False


def _find_proposals(html: str) -> int:
    """Extract proposals count from page HTML. Returns -1 if not found."""
    # JSON patterns (SSR data injected by Next.js/Apollo)
    json_patterns = [
        r'"totalApplicants"\s*:\s*(\d+)',
        r'"proposalsCount"\s*:\s*(\d+)',
        r'"proposals"\s*:\s*\{"total"\s*:\s*(\d+)',
        r'"applicantCount"\s*:\s*(\d+)',
        r'"totalProposals"\s*:\s*(\d+)',
    ]
    for pat in json_patterns:
        m = re.search(pat, html)
        if m:
            return int(m.group(1))

    # Text patterns rendered by the UI
    m = re.search(r'(?:Less|Fewer)\s+than\s+(\d+)\s+[Pp]roposals?', html)
    if m:
        return max(0, int(m.group(1)) - 1)

    m = re.search(r'(\d+)\s+to\s+(\d+)\s+[Pp]roposals?', html)
    if m:
        return int(m.group(1))  # return lower bound

    m = re.search(r'(\d+)\+\s+[Pp]roposals?', html)
    if m:
        return int(m.group(1))

    # aria-label or data attributes
    m = re.search(r'[Pp]roposals?[^"]*"[^"]*(\d+)', html)
    if m:
        val = int(m.group(1))
        if val < 1000:  # sanity check
            return val

    return -1


def _find_client(html: str) -> dict:
    out = {}
    # Payment verification
    if re.search(r'[Pp]ayment\s+[Vv]erified', html):
        out["client_verified"] = True
    elif re.search(r'[Pp]ayment\s+[Uu]nverified', html):
        out["client_verified"] = False

    # Total spent — "$5K+", "$1M+", "$150 spent"
    m = re.search(r'\$([\d,\.]+[KMkm]?)\+?\s*(total\s+)?spent', html, re.I)
    if m:
        raw = m.group(1).upper().replace(",", "")
        try:
            if "M" in raw:
                out["client_spent_amount"] = float(raw.replace("M", "")) * 1_000_000
            elif "K" in raw:
                out["client_spent_amount"] = float(raw.replace("K", "")) * 1_000
            else:
                out["client_spent_amount"] = float(raw)
        except ValueError:
            pass
        out["client_spent_text"] = m.group(0)

    # Also check JSON
    m = re.search(r'"totalSpent"\s*:\s*\{"amount"\s*:\s*"?([0-9.]+)"?', html)
    if m and "client_spent_amount" not in out:
        try:
            out["client_spent_amount"] = float(m.group(1))
        except ValueError:
            pass

    m = re.search(r'"paymentVerificationStatus"\s*:\s*"([^"]+)"', html)
    if m and "client_verified" not in out:
        out["client_verified"] = m.group(1).upper() == "VERIFIED"

    return out


async def _enrich_job_async(page, cipher: str) -> dict:
    url = f"https://www.upwork.com/jobs/~{cipher}"
    try:
        await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT)
        await asyncio.sleep(2.0)

        title = await page.title()
        current_url = page.url

        if "challenge" in title.lower() or "Just a moment" in title:
            return {"error": "cloudflare_challenge"}

        html = await page.content()
        proposals = _find_proposals(html)

        # Retry once if proposals not found — some pages need an extra JS cycle
        if proposals < 0:
            await asyncio.sleep(1.5)
            html = await page.content()
            proposals = _find_proposals(html)

        client = _find_client(html)

        return {
            "proposals_count": proposals,
            "client_verified": client.get("client_verified"),
            "client_spent_amount": client.get("client_spent_amount"),
            "client_spent_text": client.get("client_spent_text", ""),
            "page_title": title[:80],
            "final_url": current_url,
        }
    except Exception as e:
        return {"error": str(e)}


async def enrich_batch_async(
    jobs: list,
    max_enrichments: int = 20,
    verbose: bool = True,
) -> list:
    """
    Enrich a list of jobs using Chrome CDP.
    Modifies jobs in-place. Returns the same list.
    """
    if not _is_cdp_running():
        if verbose:
            print("  [CDP ENRICH] Chrome not running — starting...")
        if not _start_chrome():
            if verbose:
                print("  [CDP ENRICH] Could not start Chrome — skipping enrichment")
            return jobs

    from patchright.async_api import async_playwright

    candidates = [
        j for j in jobs
        if j.get("proposals_count", 0) == 0 or j.get("client_verified") is None
    ][:max_enrichments]

    if verbose:
        print(f"  [CDP ENRICH] enriching {len(candidates)}/{len(jobs)} jobs via Chrome CDP")

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")

        # Use first available context/page
        contexts = browser.contexts
        if contexts:
            ctx = contexts[0]
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        else:
            ctx = await browser.new_context()
            page = await ctx.new_page()

        enriched = 0
        for i, job in enumerate(candidates):
            # Extract cipher from URL
            cipher = ""
            url = job.get("url", "")
            if "~" in url:
                cipher = url.split("~")[-1].split("?")[0].strip()
            if not cipher:
                jid = job.get("id", "").replace("upwork_", "")
                if jid and not jid.startswith("gql_") and len(jid) > 8:
                    cipher = jid
            if not cipher:
                continue

            if verbose:
                print(f"  [CDP ENRICH] {cipher[:16]}… {job.get('title','')[:45]}")

            data = await _enrich_job_async(page, cipher)

            if "error" in data:
                if verbose:
                    print(f"    ⚠️  {data['error']}")
                continue

            if data.get("proposals_count", -1) >= 0:
                job["proposals_count"] = data["proposals_count"]
                enriched += 1

            if data.get("client_verified") is not None:
                job["client_verified"] = data["client_verified"]

            if data.get("client_spent_amount") is not None:
                amt = data["client_spent_amount"]
                job["client_spent_amount"] = amt
                job["client_spent"] = (
                    f"${amt/1e6:.0f}M+" if amt >= 1_000_000 else
                    f"${amt/1000:.0f}K+" if amt >= 1000 else
                    f"${amt:.0f}"
                )

            if i < len(candidates) - 1:
                await asyncio.sleep(RATE_LIMIT)

        if verbose:
            print(f"  [CDP ENRICH] {enriched}/{len(candidates)} enriched")

    finally:
        await pw.stop()

    return jobs


def enrich_jobs_batch(
    jobs: list,
    max_enrichments: int = 20,
    verbose: bool = True,
) -> list:
    """Sync wrapper for enrich_batch_async."""
    return asyncio.run(enrich_batch_async(jobs, max_enrichments, verbose))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m scanners.upwork_cdp_enricher <cipher_or_url>")
        sys.exit(1)

    raw = sys.argv[1]
    cipher = raw.split("~")[-1].split("?")[0].strip() if "~" in raw else raw

    async def _single_test():
        if not _is_cdp_running():
            print("Starting Chrome...")
            _start_chrome()

        from patchright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print(f"Enriching cipher: {cipher}")
        result = await _enrich_job_async(page, cipher)
        print(json.dumps(result, indent=2))
        await pw.stop()

    asyncio.run(_single_test())

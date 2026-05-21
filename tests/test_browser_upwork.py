#!/usr/bin/env python3
"""
Upwork Browser Automation Test Suite
Tests Chrome CDP connectivity, Cloudflare bypass, auth state,
job reading, proposal form navigation, and bot-detection resistance.

Usage:
    cd /Users/manidada/IntelForce/tools/upwork-mcp
    uv run python ../../tests/test_browser_upwork.py

Safe: Read-only tests only. NEVER submits anything to Upwork.
"""
import asyncio
import sys
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "upwork-mcp" / "src"))

# ── result helpers ──────────────────────────────────────────────────────────
PASS, FAIL, SKIP, WARN = "✅ PASS", "❌ FAIL", "⚠️  SKIP", "🟡 WARN"
results = []

def record(name, status, detail=""):
    results.append({"name": name, "status": status, "detail": detail})
    icon = status.split()[0]
    print(f"  {status}: {name}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"        {line}")

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ── T01 ─ Chrome CDP connection ─────────────────────────────────────────────
async def test_chrome_cdp():
    section("T01 — Chrome CDP Connection")
    import subprocess
    from upwork_mcp.browser.client import (
        is_chrome_running_with_debug, find_chrome, CDP_PORT, PROFILE_DIR
    )

    chrome = find_chrome()
    if not chrome:
        record("Chrome binary found", FAIL, "Chrome not installed")
        return False
    record("Chrome binary found", PASS, chrome)

    if not is_chrome_running_with_debug():
        print(f"  ℹ️  Chrome not running — starting with debug port {CDP_PORT}...")
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(
            [chrome, f"--remote-debugging-port={CDP_PORT}",
             f"--user-data-dir={PROFILE_DIR}",
             "--no-first-run", "--no-default-browser-check",
             "--disable-background-networking"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # Wait for Chrome to become reachable (no nested event loop)
        for _ in range(15):
            await asyncio.sleep(1)
            if is_chrome_running_with_debug():
                break

        if not is_chrome_running_with_debug():
            record("Chrome starts with debug port", FAIL,
                   f"Could not reach CDP after 15s.\n"
                   f"Run manually: \"{chrome}\" --remote-debugging-port={CDP_PORT} "
                   f"--user-data-dir={PROFILE_DIR}")
            return False

    record("Chrome running with debug port", PASS, f"CDP at localhost:{CDP_PORT}")

    # Try Patchright CDP connect
    from patchright.async_api import async_playwright
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
        ctxs = browser.contexts
        record("Patchright CDP connect", PASS,
               f"{len(ctxs)} context(s), {sum(len(c.pages) for c in ctxs)} page(s)")
        await pw.stop()
        return True
    except Exception as e:
        record("Patchright CDP connect", FAIL, str(e))
        return False


# ── T02 ─ Cloudflare bypass ─────────────────────────────────────────────────
async def test_cloudflare_bypass(browser):
    section("T02 — Cloudflare Bypass")
    page = await browser.get_page()
    t0 = time.monotonic()
    try:
        await page.goto("https://www.upwork.com/", wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        record("Navigate to upwork.com", FAIL, str(e))
        return

    elapsed = time.monotonic() - t0
    title = await page.title()
    url = page.url

    if "challenge" in title.lower() or "moment" in title.lower():
        record("Cloudflare bypass", FAIL,
               f"Got challenge page: '{title}'\n"
               f"URL: {url}\n"
               f"The Cloudflare check appeared. Try running --login first to get cf_clearance.")
        return

    if "upwork" in title.lower() or "upwork.com" in url:
        record("Cloudflare bypass", PASS,
               f"Title: '{title}' ({elapsed:.1f}s)\nURL: {url}")
    else:
        record("Cloudflare bypass", WARN,
               f"Unexpected page: '{title}'\nURL: {url}")


# ── T03 ─ Authentication state ───────────────────────────────────────────────
async def test_auth_state(browser):
    section("T03 — Authentication State")
    page = await browser.get_page()

    try:
        await page.goto("https://www.upwork.com/nx/find-work/best-matches",
                        wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        record("Navigate to find-work", FAIL, str(e))
        return False

    # Wait for Cloudflare to pass
    for _ in range(8):
        title = await page.title()
        url = page.url
        if "moment" not in title.lower():
            break
        await asyncio.sleep(2)

    title = await page.title()
    url = page.url

    if "login" in url.lower() or "account-security" in url.lower():
        record("Upwork login state", FAIL,
               f"Redirected to login. Not authenticated.\n"
               f"Run: uv run upwork-mcp --login   (in tools/upwork-mcp/)")
        return False

    if "challenge" in title.lower() or "moment" in title.lower():
        record("Upwork login state", FAIL,
               f"Cloudflare still showing after 16s: '{title}'\n"
               f"May need fresh cf_clearance cookie or manual CAPTCHA solve.")
        return False

    # Look for user session indicators
    html = await page.content()
    logged_in_signals = [
        '"isLoggedIn":true', '"userId":', '"accountId":', 'data-user',
        '/logout', 'my-profile', 'notifications',
    ]
    found = [s for s in logged_in_signals if s.lower() in html.lower()]

    if found:
        record("Upwork login state", PASS, f"Authenticated (signals: {found[:3]})")
        return True
    else:
        record("Upwork login state", WARN,
               f"Page loaded but no auth signals found.\n"
               f"Title: {title}\nURL: {url}\n"
               f"May need to run: uv run upwork-mcp --login")
        return False


# ── T04 ─ Job search + listing read ─────────────────────────────────────────
async def test_job_search(browser):
    section("T04 — Job Search + Listing Read")
    page = await browser.get_page()

    url = "https://www.upwork.com/nx/find-work/best-matches"
    try:
        await page.goto(url, wait_until="networkidle", timeout=25000)
        await asyncio.sleep(3)
    except Exception as e:
        record("Navigate find-work", WARN, f"Timeout/error: {e}")

    # Try to find job cards
    selectors = [
        '[data-test="job-tile-list"] article',
        '.job-tile', '[data-job-uid]', 'section.air3-card',
        '[data-test="UpwJob"] ', 'article.job-tile',
    ]
    job_count = 0
    job_titles = []
    for sel in selectors:
        els = await page.query_selector_all(sel)
        if els:
            for el in els[:3]:
                title_el = await el.query_selector('h2, h3, h4, [data-test="job-title"]')
                if title_el:
                    t = (await title_el.text_content() or "").strip()
                    if t:
                        job_titles.append(t[:60])
            job_count = len(els)
            break

    if job_count > 0 and job_titles:
        record("Job listings loaded", PASS,
               f"{job_count} jobs found\n  → {chr(10)+'  → '.join(job_titles[:3])}")
    elif job_count > 0:
        record("Job listings loaded", WARN,
               f"{job_count} job elements but couldn't extract titles")
    else:
        # Check what actually loaded
        title = await page.title()
        record("Job listings loaded", WARN,
               f"No job tiles found. Page: '{title}'\n"
               f"May need login or Cloudflare bypass.")

    # Check for job search via search URL
    search_url = "https://www.upwork.com/nx/search/jobs/?q=zapier+automation&sort=recency&t=1"
    try:
        await page.goto(search_url, wait_until="networkidle", timeout=20000)
        await asyncio.sleep(2)

        job_links = await page.query_selector_all('a[href*="/jobs/"]')
        titles_from_search = []
        for link in job_links[:5]:
            text = (await link.text_content() or "").strip()
            href = await link.get_attribute("href") or ""
            if text and len(text) > 10 and "/jobs/" in href:
                titles_from_search.append(text[:55])

        if titles_from_search:
            record("Job search results (zapier)", PASS,
                   f"{len(titles_from_search)} jobs\n  → {chr(10)+'  → '.join(titles_from_search[:3])}")
            return titles_from_search
        else:
            title = await page.title()
            record("Job search results (zapier)", WARN,
                   f"No job links found. Title: '{title}'")
    except Exception as e:
        record("Job search results (zapier)", WARN, str(e))

    return []


# ── T05 ─ Job detail page + data extraction ──────────────────────────────────
async def test_job_detail(browser, job_cipher="022057437758262261106"):
    section("T05 — Job Detail Page + Data Extraction")
    page = await browser.get_page()

    url = f"https://www.upwork.com/jobs/~{job_cipher}"
    try:
        await page.goto(url, wait_until="networkidle", timeout=25000)
        await asyncio.sleep(3)
    except Exception as e:
        record("Navigate job detail page", WARN, f"Timeout: {e}")

    title = await page.title()
    current_url = page.url

    if "challenge" in title.lower():
        record("Job detail page loads", FAIL,
               f"Cloudflare challenge. Cannot load job pages without valid session.")
        return {}

    record("Job detail page loads", PASS if "challenge" not in title.lower() else FAIL,
           f"Title: {title[:60]}\nURL: {current_url[:70]}")

    # Extract job data
    extracted = {}

    # Title
    for sel in ["h1", "h2", '[data-test="job-title"]']:
        el = await page.query_selector(sel)
        if el:
            text = (await el.text_content() or "").strip()
            if text:
                extracted["title"] = text[:80]
                break

    # Proposals count — try multiple patterns
    html = await page.content()
    patterns = [
        (r'"totalApplicants"\s*:\s*(\d+)', "totalApplicants"),
        (r'"proposalsCount"\s*:\s*(\d+)', "proposalsCount"),
        (r'"proposals"\s*:\s*\{"total"\s*:\s*(\d+)', "proposals.total"),
        (r'Less than (\d+)\s+Proposals?', "Less than N proposals"),
        (r'(\d+)\s+to\s+(\d+)\s+Proposals?', "N to M proposals"),
    ]
    for pat, name in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            extracted["proposals_source"] = name
            extracted["proposals_raw"] = m.group(0)[:50]
            extracted["proposals_count"] = int(m.group(1))
            break

    # Payment verification
    if "Payment verified" in html or "payment-verified" in html.lower():
        extracted["client_verified"] = True
    elif "Payment unverified" in html:
        extracted["client_verified"] = False

    # Total spent
    m = re.search(r'\$[\d,\.]+[KMkm]?\+?\s*(total\s+)?spent', html, re.I)
    if m:
        extracted["client_spent_text"] = m.group(0)

    if extracted.get("proposals_count") is not None:
        record("Proposals count extracted", PASS,
               f"{extracted['proposals_count']} proposals (via {extracted.get('proposals_source', '?')})\n"
               f"Raw: {extracted.get('proposals_raw', '')}")
    else:
        record("Proposals count extracted", WARN,
               "Not found in page HTML — may need authenticated session or different selector")

    if extracted.get("client_verified") is not None:
        record("Client verification extracted", PASS,
               f"Verified: {extracted['client_verified']}")
    else:
        record("Client verification extracted", WARN, "Not found")

    if extracted.get("title"):
        record("Job title readable", PASS, extracted["title"])

    return extracted


# ── T06 ─ Apply form navigation ──────────────────────────────────────────────
async def test_apply_form(browser, job_cipher="022057437758262261106"):
    section("T06 — Apply Form Navigation (read-only, will NOT submit)")
    page = await browser.get_page()

    # Navigate to job page
    url = f"https://www.upwork.com/jobs/~{job_cipher}"
    await page.goto(url, wait_until="networkidle", timeout=25000)
    await asyncio.sleep(2)

    # Look for Apply button
    apply_selectors = [
        'button[data-test="apply-button"]',
        'button:has-text("Apply Now")',
        'a:has-text("Apply Now")',
        '[data-test="apply-button"]',
        'button:has-text("Apply")',
    ]
    apply_btn = None
    for sel in apply_selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                apply_btn = el
                record("Apply button found", PASS, f"Selector: {sel}")
                break
        except Exception:
            pass

    if not apply_btn:
        # Check if already applied or job closed
        html = await page.content()
        if "applied" in html.lower() or "proposal submitted" in html.lower():
            record("Apply button found", SKIP, "Already applied to this job")
        elif "job is closed" in html.lower() or "no longer available" in html.lower():
            record("Apply button found", SKIP, "Job is closed/unavailable")
        else:
            record("Apply button found", WARN,
                   "No apply button found. May need login or different job.")
        return

    # Click apply to open the proposal form
    try:
        await apply_btn.click()
        await asyncio.sleep(3)

        # Check form elements
        form_checks = {
            "Cover letter textarea": [
                'textarea[name*="cover"]',
                '[data-test="cover-letter-input"]',
                'textarea',
            ],
            "Bid/rate input": [
                '[data-test="bid-input"]',
                'input[name*="bid"]',
                'input[name*="amount"]',
                'input[type="number"]',
            ],
            "Submit button": [
                'button[type="submit"]',
                '[data-test="submit-proposal"]',
                'button:has-text("Submit")',
            ],
        }

        for label, selectors in form_checks.items():
            found = False
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        record(f"Form field: {label}", PASS, f"Selector: {sel}")
                        found = True
                        break
                except Exception:
                    pass
            if not found:
                record(f"Form field: {label}", WARN, "Not found with known selectors")

        # Check connects required
        html = await page.content()
        connects_m = re.search(r'(\d+)\s*Connects?', html, re.I)
        if connects_m:
            record("Connects cost readable", PASS,
                   f"{connects_m.group(1)} Connects required")
        else:
            record("Connects cost readable", WARN, "Could not find connects cost")

        # IMPORTANT: Do NOT submit — navigate away
        await page.goto("https://www.upwork.com/nx/find-work/best-matches",
                        wait_until="domcontentloaded")
        record("Form navigation (read-only)", PASS, "Navigated away without submitting")

    except Exception as e:
        record("Apply form interaction", FAIL, str(e))


# ── T07 ─ Message inbox ──────────────────────────────────────────────────────
async def test_messages(browser):
    section("T07 — Message Inbox Navigation")
    page = await browser.get_page()
    try:
        await page.goto("https://www.upwork.com/nx/messages/",
                        wait_until="networkidle", timeout=20000)
        await asyncio.sleep(2)
    except Exception as e:
        record("Navigate messages page", WARN, f"Timeout: {e}")
        return

    title = await page.title()
    url = page.url

    if "login" in url.lower():
        record("Messages page", FAIL, "Redirected to login")
        return

    if "challenge" in title.lower():
        record("Messages page", FAIL, "Cloudflare challenge")
        return

    # Look for conversation list
    html = await page.content()
    msg_signals = ["conversation", "inbox", "message-thread", "chat"]
    found = [s for s in msg_signals if s.lower() in html.lower()]

    record("Messages inbox accessible", PASS if found else WARN,
           f"Title: {title}\nSignals: {found}")


# ── T08 ─ Anti-bot stress test ───────────────────────────────────────────────
async def test_antibot(browser):
    section("T08 — Anti-Bot Detection Resistance")
    page = await browser.get_page()

    urls = [
        "https://www.upwork.com/nx/search/jobs/?q=zapier&sort=recency&t=1",
        "https://www.upwork.com/nx/search/jobs/?q=n8n+workflow&sort=recency&t=1",
        "https://www.upwork.com/nx/search/jobs/?q=make.com+automation&sort=recency&t=1",
    ]

    challenges = 0
    for url in urls:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(1.5)
            title = await page.title()
            if "challenge" in title.lower() or "moment" in title.lower():
                challenges += 1
        except Exception:
            challenges += 1

    if challenges == 0:
        record("3-page rapid navigation", PASS,
               "No Cloudflare challenges triggered")
    elif challenges <= 1:
        record("3-page rapid navigation", WARN,
               f"{challenges}/3 pages triggered challenge — acceptable but monitor")
    else:
        record("3-page rapid navigation", FAIL,
               f"{challenges}/3 pages triggered Cloudflare — bot detection active")


# ── main ─────────────────────────────────────────────────────────────────────
async def main():
    print("\n" + "═"*60)
    print("  UPWORK BROWSER AUTOMATION — PRODUCTION READINESS TEST")
    print("═"*60)
    print("  Pipeline: /Users/manidada/IntelForce")
    print("  Profile:  ~/.upwork-mcp/chrome-profile")
    print("  SAFE: Read-only. Will NOT submit anything to Upwork.")
    print("═"*60)

    # T01 — Chrome CDP
    cdp_ok = await test_chrome_cdp()
    if not cdp_ok:
        print("\n  ⛔ Chrome CDP failed — cannot continue.\n")
        print("  Fix: Ensure Chrome is installed and accessible, then rerun.")
        _print_summary()
        return 1

    # Create browser instance
    from upwork_mcp.browser.client import UpworkBrowser
    browser = UpworkBrowser(timeout=30000)
    try:
        await browser.start()
    except Exception as e:
        record("Browser instance created", FAIL, str(e))
        _print_summary()
        return 1

    # T02–T08
    await test_cloudflare_bypass(browser)
    auth_ok = await test_auth_state(browser)

    if not auth_ok:
        print("\n  ⚠️  Not logged in. Remaining tests may fail or be limited.")
        print("  Fix: Run  uv run upwork-mcp --login  then rerun tests.\n")

    await test_job_search(browser)

    # Use a real job cipher from our last scan
    JOB_CIPHER = "022057437758262261106"  # "Automation Specialist (n8n/Make/Zapier)"
    await test_job_detail(browser, JOB_CIPHER)
    await test_apply_form(browser, JOB_CIPHER)
    await test_messages(browser)
    await test_antibot(browser)

    await browser.close()
    return _print_summary()


def _print_summary():
    print("\n" + "═"*60)
    print("  TEST SUMMARY")
    print("═"*60)

    passed = [r for r in results if "PASS" in r["status"]]
    failed = [r for r in results if "FAIL" in r["status"]]
    warned = [r for r in results if "WARN" in r["status"] or "SKIP" in r["status"]]

    print(f"  ✅ PASS: {len(passed)}")
    print(f"  🟡 WARN: {len(warned)}")
    print(f"  ❌ FAIL: {len(failed)}")

    if failed:
        print("\n  BLOCKERS:")
        for r in failed:
            print(f"  • {r['name']}")
            if r["detail"]:
                print(f"    {r['detail'].splitlines()[0]}")

    if warned:
        print("\n  WARNINGS:")
        for r in warned:
            print(f"  • {r['name']}")

    print("\n  PRODUCTION READINESS: ", end="")
    if not failed:
        print("READY ✅")
        return 0
    elif len(failed) <= 2 and any("login" in r["name"].lower() or "auth" in r["detail"].lower()
                                    for r in failed if r["detail"]):
        print("BLOCKED ON LOGIN ⚠️ (run --login first)")
        return 1
    else:
        print(f"NOT READY ❌ ({len(failed)} blocker(s))")
        return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


# ── T09 ─ Batch enrichment reliability ──────────────────────────────────────
async def test_batch_enrichment(browser):
    section("T09 — Batch Enrichment Reliability (proposals count at scale)")
    
    # Use 5 jobs from our known scan results
    test_ciphers = [
        ("022057437758262261106", "Automation Specialist"),
        ("022057188644408702322", "Zapier expert Squarespace"),
        ("022057158691792572103", "AI Voice Agent"),
        ("022055916786474398736", "n8n Developer Wix+Claude"),
        ("022055691499869521963", "Build AI WhatsApp"),
    ]
    
    page = await browser.get_page()
    
    from scanners.upwork_cdp_enricher import _enrich_job_async
    import sys
    sys.path.insert(0, '/Users/manidada/IntelForce')
    
    found = 0
    failed = 0
    low_comp = []
    
    for cipher, label in test_ciphers:
        r = await _enrich_job_async(page, cipher)
        p = r.get("proposals_count", -1)
        err = r.get("error", "")
        if err:
            failed += 1
        elif p >= 0:
            found += 1
            if p <= 15:
                low_comp.append(f"{label} ({p} props)")
        else:
            failed += 1
    
    reliability = found / len(test_ciphers) * 100
    
    if reliability >= 80:
        record("Batch enrichment reliability", PASS,
               f"{found}/{len(test_ciphers)} successful ({reliability:.0f}%)\n"
               f"Low-competition jobs found: {low_comp or 'none in this batch'}")
    elif reliability >= 60:
        record("Batch enrichment reliability", WARN,
               f"{found}/{len(test_ciphers)} successful ({reliability:.0f}%) — below 80% target")
    else:
        record("Batch enrichment reliability", FAIL,
               f"Only {found}/{len(test_ciphers)} enriched ({reliability:.0f}%) — unreliable")

#!/usr/bin/env python3
"""
Job enricher — fetches Upwork job detail pages to extract proposals count
and client data. Uses curl_cffi with Chrome TLS fingerprint. No browser.

This runs AFTER the bulk GraphQL scan. Only enriches jobs that passed the
keyword + budget pre-filter (typically 0-15 per scan). ~800ms per job.
"""
import json, re, sys, time
from pathlib import Path

try:
    from curl_cffi import requests as cr
except ImportError:
    print("ERROR: pip3 install curl_cffi", file=sys.stderr); sys.exit(1)

RATE_LIMIT = 0.8   # seconds between requests
TIMEOUT    = 12    # per-job timeout


def _extract_next_data(html: str) -> dict:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html, re.DOTALL
    )
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {}


def _walk(obj, depth=0):
    """Yield every (key, value) pair recursively, stopping at depth 10."""
    if depth > 10:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _walk(v, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for item in obj[:20]:
            yield from _walk(item, depth + 1)


def _find_proposals(obj) -> int:
    """Search nested JSON for any proposals-count field."""
    KEYS = {
        "totalapplicants", "proposalscount", "proposals_count",
        "applicantcount", "total",
    }
    for k, v in _walk(obj):
        if k.lower().replace("-", "").replace("_", "") in {
            x.replace("_","") for x in KEYS
        }:
            if isinstance(v, (int, float)) and 0 <= v < 1000:
                return int(v)
    return -1   # -1 = not found


def _find_client(obj) -> dict:
    result = {}
    for k, v in _walk(obj):
        kl = k.lower().replace("_", "").replace("-", "")
        if kl in ("paymentverificationstatus", "ispaymentmethodverified"):
            result["client_verified"] = str(v).upper() in ("VERIFIED", "TRUE", "1")
        if kl in ("totalspent",):
            if isinstance(v, dict):
                amt = v.get("amount") or v.get("rawValue") or v.get("rawvalue") or 0
                try:
                    result["client_spent_amount"] = float(amt)
                except (TypeError, ValueError):
                    pass
            elif isinstance(v, (int, float)):
                result["client_spent_amount"] = float(v)
    return result


def _spent_str(amount) -> str:
    if not amount:
        return ""
    try:
        a = float(amount)
    except (TypeError, ValueError):
        return ""
    if a >= 1_000_000:
        return f"${a/1e6:.0f}M+"
    if a >= 1000:
        return f"${a/1000:.0f}K+"
    return f"${a:.0f}"


def enrich_job(cipher: str, visitor_token: str = None) -> dict:
    """
    Fetch a single job page and return enrichment data.
    Returns: {"proposals_count": int, "client_verified": bool|None,
              "client_spent": str, "client_spent_amount": float|None}
    Returns {} on complete failure.
    """
    url = f"https://www.upwork.com/jobs/~{cipher}"
    hdrs = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    cookies = {}
    if visitor_token:
        cookies["visitor_gql_token"] = visitor_token

    try:
        r = cr.get(url, impersonate="chrome124", timeout=TIMEOUT,
                   headers=hdrs, cookies=cookies, allow_redirects=True)
        if r.status_code != 200:
            return {}
        html = r.text

        out = {"proposals_count": -1, "client_verified": None,
               "client_spent": "", "client_spent_amount": None}

        # --- Strategy 1: __NEXT_DATA__ Apollo cache ---
        next_data = _extract_next_data(html)
        if next_data:
            props = _find_proposals(next_data)
            if props >= 0:
                out["proposals_count"] = props
            cdata = _find_client(next_data)
            if "client_verified" in cdata:
                out["client_verified"] = cdata["client_verified"]
            if "client_spent_amount" in cdata:
                out["client_spent_amount"] = cdata["client_spent_amount"]
                out["client_spent"] = _spent_str(cdata["client_spent_amount"])

        # --- Strategy 2: Raw JSON fragments in HTML ---
        if out["proposals_count"] < 0:
            for pat in (
                r'"totalApplicants"\s*:\s*(\d+)',
                r'"proposalsCount"\s*:\s*(\d+)',
                r'"proposals"\s*:\s*\{\s*"total"\s*:\s*(\d+)',
            ):
                m = re.search(pat, html)
                if m:
                    out["proposals_count"] = int(m.group(1))
                    break

        # --- Strategy 3: Visible text patterns ---
        if out["proposals_count"] < 0:
            m = re.search(r'"proposals":\{"total":(\d+)', html)
            if m:
                out["proposals_count"] = int(m.group(1))
            else:
                # "Less than 5", "5 to 10", "10 to 15" patterns on page
                m = re.search(
                    r'(?:Less than|Fewer than)\s*(\d+)\s*[Pp]roposal',
                    html
                )
                if m:
                    out["proposals_count"] = int(m.group(1)) - 1
                else:
                    m = re.search(r'(\d+)\s+[Pp]roposals?\s+(?:submitted|so far)', html)
                    if m:
                        out["proposals_count"] = int(m.group(1))

        # --- Strategy 4: Payment verification text ---
        if out["client_verified"] is None:
            if "Payment verified" in html or "payment-verified" in html:
                out["client_verified"] = True
            elif "Payment unverified" in html:
                out["client_verified"] = False

        # --- Strategy 5: Total spent from visible text ---
        if not out["client_spent"]:
            m = re.search(r'\$(\d[\d,\.]*[KMkm]?)\+?\s*(?:total\s+)?spent', html, re.I)
            if m:
                out["client_spent"] = f"${m.group(1)} spent"

        return out

    except Exception as e:
        print(f"  [ENRICH] err {cipher[:12]}: {e}", file=sys.stderr)
        return {}


def enrich_jobs_batch(
    jobs: list,
    visitor_token: str = None,
    max_enrichments: int = 20,
    verbose: bool = True,
) -> list:
    """
    Enrich a list of jobs in-place. Only fetches jobs without complete data.
    Returns the same list with enriched fields merged in.
    """
    # Jobs that need enrichment: missing proposals count OR client status
    candidates = [
        j for j in jobs
        if j.get("proposals_count", 0) == 0 or j.get("client_verified") is None
    ][:max_enrichments]

    if verbose:
        print(f"  [ENRICH] enriching {len(candidates)}/{len(jobs)} jobs")

    enriched = 0
    for i, job in enumerate(candidates):
        # Extract cipher from URL or ID
        cipher = ""
        url = job.get("url", "")
        if "~" in url:
            cipher = url.split("~")[-1].split("?")[0].strip()
        if not cipher:
            jid = job.get("id", "")
            # Format: "upwork_<cipher>" when cipher is alphanumeric
            candidate = jid.replace("upwork_", "")
            if candidate and not candidate.startswith("gql_") and len(candidate) > 10:
                cipher = candidate

        if not cipher:
            continue

        if verbose:
            print(f"  [ENRICH] {cipher[:16]}… {job.get('title','')[:45]}")

        data = enrich_job(cipher, visitor_token)
        if data:
            if data.get("proposals_count", -1) >= 0:
                job["proposals_count"] = data["proposals_count"]
            if data.get("client_verified") is not None:
                job["client_verified"] = data["client_verified"]
            if data.get("client_spent"):
                job["client_spent"] = data["client_spent"]
            if data.get("client_spent_amount") is not None:
                job["client_spent_amount"] = data["client_spent_amount"]
            enriched += 1

        if i < len(candidates) - 1:
            time.sleep(RATE_LIMIT)

    if verbose:
        print(f"  [ENRICH] {enriched} enriched successfully")
    return jobs


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Test enricher against a single job URL")
    p.add_argument("url_or_cipher", help="Full job URL or cipher (the ~xxx part)")
    args = p.parse_args()
    raw = args.url_or_cipher
    cipher = raw.split("~")[-1].split("?")[0].strip() if "~" in raw else raw
    print(f"Enriching cipher: {cipher}")
    result = enrich_job(cipher)
    print(json.dumps(result, indent=2))

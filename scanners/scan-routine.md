# Scan Routine

Operating schedule for job discovery. All times in BST (Europe/London).

## Daily Schedule

| Time | Sources | Notes |
|------|---------|-------|
| 08:00 BST | RSS + Brave | UK/EU morning postings |
| 12:00 BST | RSS + Brave | US morning |
| 16:00 BST | RSS + Brave | US late morning |
| 20:00 BST | RSS + Brave | Evening catch-up |
| 00:00 BST | RSS + Brave | Overnight US |

## Commands

```bash
# RSS scan (no key required)
python3 scanners/upwork_rss_scanner.py

# Brave search scan (requires BRAVE_API_KEY)
python3 scripts/brave_job_search.py

# Score all new jobs
python3 scripts/job_scorer.py --all

# Generate proposals for scored jobs
python3 scripts/proposal_generator.py --min-score 60

# Full pipeline (discover → score → propose)
python3 scripts/revenue_pipeline.py --no-dry-run --gate-mode manual --limit 20

# Check queue governance
python3 scripts/queue_blocker_check.py
```

## Platform Priority

1. **Upwork** — primary. Best client quality, highest volume, best budgets.
2. Fiverr — secondary. Productized services.
3. Freelancer.com — volume play, more price-sensitive.
4. PeoplePerHour — UK-focused, GBP payments.

## Upwork Search URLs (rotate through daily)

### Tier 1 — Easy money (scan every cycle)
- zapier automation: https://www.upwork.com/nx/search/jobs/?q=zapier%20automation&sort=recency
- make automation: https://www.upwork.com/nx/search/jobs/?q=make%20automation&sort=recency
- api integration: https://www.upwork.com/nx/search/jobs/?q=api%20integration&sort=recency
- chatbot: https://www.upwork.com/nx/search/jobs/?q=chatbot&sort=recency
- web scraping: https://www.upwork.com/nx/search/jobs/?q=web%20scraping&sort=recency
- discord bot: https://www.upwork.com/nx/search/jobs/?q=discord%20bot&sort=recency
- google sheets automation: https://www.upwork.com/nx/search/jobs/?q=google%20sheets%20automation&sort=recency

### Tier 2 — Medium complexity (2x daily)
- n8n: https://www.upwork.com/nx/search/jobs/?q=n8n&sort=recency
- openai integration: https://www.upwork.com/nx/search/jobs/?q=openai%20integration&sort=recency
- langchain: https://www.upwork.com/nx/search/jobs/?q=langchain&sort=recency

### Tier 3 — High value (daily)
- ai agent: https://www.upwork.com/nx/search/jobs/?q=ai%20agent&sort=recency
- voice agent: https://www.upwork.com/nx/search/jobs/?q=voice%20agent&sort=recency

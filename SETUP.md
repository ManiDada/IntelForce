# Setup Guide

## Prerequisites

- Python 3.9+
- pip
- sqlite3 (usually built into Python)

## Installation

```bash
git clone https://github.com/ManiDada/IntelForce.git
cd IntelForce
pip install -r requirements.txt
```

## Database Setup

```bash
python3 scripts/setup_database.py
```

Expected output:
```
Initializing IntelForce database...
✅ Database ready: 12 tables
   _migrations: 3 rows
   jobs: 0 rows
   ...
```

## Environment Variables

```bash
cp .env.example .env
# Edit .env with your values
```

Required for full functionality:
- `BRAVE_API_KEY` — get free key at https://api.search.brave.com/ (free tier: 2,000 queries/month)

## First Run

```bash
# 1. Seed with existing jobs
python3 scripts/setup_database.py

# 2. Run RSS discovery
python3 scanners/upwork_rss_scanner.py

# 3. Score all jobs
python3 scripts/job_scorer.py --all

# 4. Generate proposals (dry-run)
python3 scripts/revenue_pipeline.py --dry-run --gate-mode manual --limit 20

# 5. Check queue state
python3 scripts/queue_blocker_check.py

# 6. Run for real when ready
python3 scripts/revenue_pipeline.py --no-dry-run --gate-mode manual --limit 20
```

## Tests

```bash
pytest tests/ -v
```

## Upwork Account (Required Before First Submission)

The system generates proposals but doesn't submit them. Submission is always manual.

To submit proposals:
1. Create Upwork freelancer account at upwork.com
2. Complete profile (photo, skills, overview, portfolio)
3. Get profile approved (usually 24–48h)
4. Review proposals in `proposals/pending/`
5. Submit manually through Upwork interface

## Ongoing Operations

Daily:
```bash
# Morning (08:00): RSS scan + score + propose
python3 scanners/upwork_rss_scanner.py
python3 scripts/revenue_pipeline.py --no-dry-run --gate-mode manual --limit 20

# Check queue
python3 scripts/queue_blocker_check.py
```

With Brave API key:
```bash
python3 scripts/brave_job_search.py
```

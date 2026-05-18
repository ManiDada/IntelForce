# IntelForce — Autonomous Freelance Revenue Engine

An autonomous system for finding, scoring, proposing on, winning, and delivering automation/AI/integration jobs on Upwork.

**Target:** £20K/month through speed, scoring discipline, and a continuous learning loop.

## Quick Start

```bash
# 1. Setup
pip install -r requirements.txt
python3 scripts/setup_database.py

# 2. Discover jobs
python3 scanners/upwork_rss_scanner.py           # RSS (no key needed)
BRAVE_API_KEY=<key> python3 scripts/brave_job_search.py   # Search-based

# 3. Score + generate proposals (dry-run first)
python3 scripts/revenue_pipeline.py --dry-run --gate-mode manual --limit 20

# 4. Check what's in the queue
python3 scripts/queue_blocker_check.py

# 5. Run for real (writes proposals to proposals/pending/)
python3 scripts/revenue_pipeline.py --no-dry-run --gate-mode manual --limit 20

# 6. Run tests
pytest tests/
```

## Architecture

```
discover → qualify → score → propose → [human gate] → submit → track → deliver
```

### Pipeline Stages

| Stage | Status | Notes |
|-------|--------|-------|
| `discovered` | ✅ | Job found by scanner |
| `qualified` | ✅ | Passed initial filters |
| `scored` | ✅ | EV score calculated |
| `proposal_ready` | ✅ | Proposal generated |
| `needs_approval` | ✅ | Queued for human review |
| `proposal_sent` | 🔒 | Manually sent by operator |
| `interview` | → | Client responded |
| `won` | → | Job accepted |
| `building` | → | Active development |
| `qa` | → | Testing |
| `delivered` | → | Shipped to client |
| `paid` | → | Invoice settled |

### Scoring Model

**EV Model** (pipeline/scoring.py):
```
win_probability = max(10%, 95% - min(80%, competition × 1.2))
speed_score = 90 if competition ≤ 10 else 65 if ≤ 30 else 40
job_score = (skill_score × 0.7) + (win_probability × 0.3)
EV = (job_score × 0.5) + (win_probability × 0.3) + (speed_score × 0.2)
```

Gate thresholds:
- EV ≥ 82 + confidence ≥ 85 → AUTO_SEND_ELIGIBLE (currently OFF)
- EV ≥ 70 → REVIEW_AND_SEND (human approves)
- EV < 70 → HOLD

## Directory Structure

```
IntelForce/
├── pipeline/           Production pipeline modules
│   ├── models.py       Job + ProposalDraft dataclasses
│   ├── db.py           SQLite connection + migrations
│   ├── ingestion.py    Load jobs from jobs.json
│   ├── scoring.py      EV scoring model
│   ├── proposal.py     Proposal generation
│   ├── approval.py     Gate decision logic
│   ├── outcomes.py     Outcome + idempotency logging
│   ├── runner.py       Full pipeline orchestrator
│   └── migrations/     SQL schema files
├── scripts/            CLI scripts
│   ├── revenue_pipeline.py    Main entry point
│   ├── job_scorer.py          Standalone scorer
│   ├── proposal_generator.py  Standalone proposal writer
│   ├── queue_blocker_check.py Governance checker
│   ├── brave_job_search.py    Brave Search discovery
│   └── setup_database.py      DB init
├── scanners/           Discovery sources
│   ├── upwork_rss_scanner.py  RSS (no login needed)
│   └── upwork-scanner.js      Browser automation (requires login)
├── data/               Persistent data
│   ├── jobs.db         SQLite database (gitignored)
│   ├── jobs.json       Ingestion source
│   └── queue-governance-state.json
├── proposals/          Proposal lifecycle
│   ├── pending/        Generated, awaiting review
│   ├── sent/           Approved and submitted
│   └── rejected/       Skipped
├── build-packs/        Delivery briefs for won jobs
├── qa-reports/         QA artifacts
├── templates/          Proposal + delivery templates
├── tests/              Test suite
└── projects/           Delivered project scaffolds
```

## Key Rules (Non-Negotiable)

1. **Manual gate first** — `dry_run=true`, `gate_mode=manual`, `allow_send=false` until 10+ successful manual approvals
2. **Never auto-submit** — humans stay in the loop for actual Upwork submission
3. **Proposal promises = acceptance criteria** — never promise what you can't deliver
4. **Track everything** — every job in DB, every outcome logged
5. **Quality compounds** — reviews drive future win rates, never ship sloppy work

## Environment Variables

```bash
BRAVE_API_KEY=          # From brave.com/search/api (required for Brave discovery)
JOBS_JSON_PATH=         # Override jobs.json path (testing only)
UPWORK_USERNAME=        # For browser-based scanner (optional)
UPWORK_PASSWORD=        # For browser-based scanner (optional)
```

## Current Status

- **Pipeline:** Fully built ✅
- **Scoring:** Calibrated on real Upwork jobs ✅
- **Proposals:** 2 scored proposals ready in data/jobs.json ✅
- **Upwork account:** Not yet live 🔒 (PRIMARY BLOCKER)
- **Revenue:** £0 (pre-launch)

See `data/queue-governance-state.json` for current pipeline state.

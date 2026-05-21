# IntelForce — Session Context Document
**Generated:** 2026-05-21 ~11:45 UTC
**Purpose:** Full instance context for continuing work in a new Claude Code session (VS Code terminal)

---

## 1. What This System Is

**intel-force-engine** is an autonomous AI-native freelance revenue operation running on cortextOS. The goal is to reach £20K/month on Upwork through systematic job discovery, scoring, proposal drafting, and delivery — with less than 10 hours of human input per week.

**North star:** A fully autonomous, self-improving commercial AI operation that generates reliable income with less than 10 hours of human input per week, proving an AI-native system can run an entire freelance business end-to-end.

---

## 2. System Architecture

### cortextOS Layer (the agent framework)
- **Location:** `/Users/manidada/cortextos/`
- **Framework:** cortextOS Node.js — multi-agent orchestration system
- **Instance:** `default` at `~/.cortextos/default/`

### Agents Running

| Agent | Role | Telegram Bot | Status |
|-------|------|-------------|--------|
| **harry** | Orchestrator — chief of staff, morning/evening briefings, goal cascade, fleet health | Bot token in `.env` | Running via PM2 |
| **analyst** | System health monitoring, theta-wave improvement cycles, metrics tracking | Separate bot | Running via PM2 |

### Agent Directories
- `orgs/intel-force-engine/agents/harry/` — harry's config, memory, skills, bootstrap files
- `orgs/intel-force-engine/agents/analyst/` — analyst's config, memory, skills

### Key Bootstrap Files (harry)
- `IDENTITY.md` — harry's role and vibe (orchestrator, chief of staff)
- `SOUL.md` — behavioral principles (day/night mode, autonomy rules)
- `GOALS.md` — current goals (generated from goals.json)
- `SYSTEM.md` — team roster and org context
- `USER.md` — Mani's preferences (dynamic/brief comms, no emojis, morning summaries)
- `HEARTBEAT.md` — heartbeat checklist (runs every 4h)
- `MEMORY.md` — long-term memory
- `TOOLS.md` — tool reference
- `GUARDRAILS.md` — behavioral guardrails

### Crons (daemon-managed, survive restarts)
```
harry crons (cortextos bus list-crons harry):
- heartbeat          4h        — fleet health check, inbox sweep
- check-approvals    2h        — pending approvals and human tasks
- morning-review     0 8 * * * — daily briefing + goal cascade (08:00 BST)
- evening-review     0 18 * * * — day summary + overnight planning (18:00 BST)
- weekly-review      0 8 * * 0 — weekly synthesis (Sunday 08:00 BST)
- pipeline-discovery-morning    0 10 * * * — Upwork pipeline run
- pipeline-discovery-afternoon  0 15 * * * — Upwork pipeline run
- pipeline-discovery-evening    0 20 * * * — Upwork pipeline run
- pipeline-discovery-midnight   0 0 * * *  — Upwork pipeline run
```

### Communication
- User → harry: Telegram (chat_id: 8893758382)
- harry → analyst: `cortextos bus send-message analyst normal '<msg>'`
- harry → user: `cortextos bus send-telegram 8893758382 '<msg>'`

---

## 3. The IntelForce Pipeline

### Location
`/Users/manidada/IntelForce/`

### What's Built (fully functional)
```
/scanners/
  upwork_rss_scanner.py     — RSS scanner (DEPRECATED, Upwork 410'd the endpoint)
  serper_job_search.py      — Serper.dev scanner (built, but Google doesn't index live Upwork jobs)

/scripts/
  revenue_pipeline.py       — Full pipeline CLI: ingest → score → propose → gate → log
  job_scorer.py             — Standalone job scorer (EV model + root model)
  proposal_generator.py     — Standalone proposal writer
  queue_blocker_check.py    — Governance checker
  notify_scored_jobs.py     — Telegram notifications for scored jobs (EV>=70, daily cap 8)
  poll_and_notify.sh        — Polling daemon (runs scanner → pipeline → notify)
  brave_job_search.py       — Brave Search scanner (built, needs CC for API key)
  setup_database.py         — DB init and migrations

/pipeline/
  scoring.py                — Dual EV + root scoring model
  approval.py               — Gate logic (REVIEW_EV=70, AUTO_SEND_EV=82)
  proposal.py               — Job-type-aware proposal generation
  db.py                     — SQLite connection, WAL mode, migrations
  ingestion.py              — Load/normalize jobs → DB
  outcomes.py               — Win/loss logging and metrics
  runner.py                 — Full pipeline orchestrator

/data/
  jobs.json                 — Job index (currently has 2 pre-launch seed jobs)
  jobs.db                   — SQLite database (migrations applied)
  notified_jobs.json        — IDs of jobs already notified (dedup)
  queue-governance-state.json

/proposals/
  pending/                  — Proposals awaiting Mani review
  held/
    AI-GTM-Engineer_EV91.6_hold-until-JSS.md  — HELD: submit after 3 wins + positive JSS

/build-packs/
  case-study-zapier-ecommerce.md      — Portfolio case study (Shopify → Sheets + Slack + Trello)
  case-study-make-lead-capture.md     — Portfolio case study (B2B lead capture, Make.com)
  case-study-n8n-webhook-router.md    — Portfolio case study (Pipedrive webhook → Sheets + Slack)
  catalog-listings-spec.md            — 3 Upwork Project Catalog listing specs (ready to create)
  upwork-profile-draft.md             — Full profile copy (headline, overview, skills, hourly rate)

/research/
  upwork-cold-start-playbook.md       — How freelancers land first 5 jobs with 0 JSS

/config/
  scoring_config.json       — Current scoring config (see below)
```

### scoring_config.json (current state)
```json
{
  "mode": "manual_intake_cold_start",
  "target_keywords": ["zapier", "make.com", "n8n", "makecom", "make com"],
  "budget_min_gbp": 150,
  "budget_max_gbp": 400,
  "max_competing_proposals": 15,
  "require_verified_client": true,
  "require_spend_history": true,
  "score_threshold_ev": 65,
  "daily_cap": 8,
  "data_source": "serper",
  "poll_interval_minutes": 64,
  "queries_per_run": 3,
  "speed_weight": 0.0,
  "skill_weight": 0.80,
  "competition_weight": 0.20,
  "mode": "manual_intake_cold_start",
  "portfolio_penalty": -15,
  "portfolio_threshold": 2,
  "portfolio_items": 2,
  "portfolio_keywords": ["portfolio", "previous work", "examples", "loom", "show us", "similar work", "case study"],
  "red_flag_keywords": ["complex", "multi-step", "multiple integrations", "code", "script", "various", "several", "many", "full", "custom code", "development", "build from scratch"]
}
```

### JOB_CRITERIA.md (cold-start mode — current)
- Target: Zapier, Make.com, or n8n visual workflow builds ONLY
- Budget: Fixed price £150-400
- Complexity: Single clear deliverable (one automation, one connection)
- Client: Verified payment, spend history required
- Competition: Under 15 proposals (hard filter)
- Red flags: code-heavy, multi-step, complex, vague briefs

---

## 4. Discovery Problem (Root Cause)

**Automated job discovery is currently broken.** Three approaches failed:
1. **Upwork RSS** — endpoint is HTTP 410 Gone (deprecated by Upwork)
2. **Brave Search API** — requires credit card even for free tier
3. **Serper.dev (Google)** — Google does not index live Upwork job listings

**Current approach: Manual intake**
- Mani finds jobs on Upwork by browsing directly
- Pastes job description to harry via Telegram
- Harry scores immediately (hard filter → EV score → go/no-go)
- If go: pipeline generates proposal draft, Mani reviews and submits manually on Upwork

**Long-term fix (not built yet):**
Browser automation with Mani's logged-in Upwork session (Playwright). Upwork's JS-rendered job search requires a logged-in browser session — no API or search engine approach works. This is the `browser-based scanner (upwork-scanner.js)` listed in BUILD-COMPLETE.md as not done.

**PM2 daemon (configured but producing 0 jobs due to above):**
```bash
pm2 start /Users/manidada/IntelForce/ecosystem.discovery.config.js
# Runs poll_and_notify.sh every 64 minutes
# Will work once a real data source is connected
```

---

## 5. Current Pipeline State

### What works right now
- **Scoring model** — fully functional (EV = skill×0.8 + competition×0.2, gate at EV>=70)
- **Proposal generation** — fully functional
- **Telegram notifications** — fully functional (harry sends via `cortextos bus send-telegram`)
- **Manual intake** — harry scores jobs Mani pastes, generates proposals

### What doesn't work
- **Automated discovery** — all approaches blocked (see above)
- **Browser automation** — not built

### Jobs scored in session (all no-go)
8 jobs scored on 2026-05-19. All rejected before portfolio was lifted. Breakdown:
- Wrong category: chatbot avatar design, SMTP debugging, AI voice receptionist, AI chatbot SaaS
- Budget fail: Google Sheets to Lark ($25), AI voice receptionist (€100)
- Too complex: Make.com appraisal register, solar n8n lead system, Assembly portal
- Ethics conflict: SMTP job explicitly banned AI-generated code

Portfolio gap was a recurring secondary blocker. **Portfolio gap is now closed** (portfolio_items=2).

---

## 6. What Needs to Happen Next

### Immediate (today)
1. **Mani: Create 3 Upwork Project Catalog listings** — copy is in `/IntelForce/build-packs/catalog-listings-spec.md` and was sent via Telegram. This bypasses competitive proposals entirely — clients buy directly.
2. **Mani: Update Upwork profile** — headline, overview, skills, hourly rate. Copy is in `/IntelForce/build-packs/upwork-profile-draft.md`.
3. **Mani: Resume manual job intake** — paste jobs here, harry scores them with hard filters applied upfront.

### Short-term (this week)
4. **Build the browser-based Upwork scanner** — this is the real discovery fix. Playwright + logged-in Upwork session, polls every 8-10 minutes, extracts job listings, feeds pipeline. Estimate: 4-8 hours worker session.
5. **First go decision** — once a job passes hard filters and scores EV>=70, generate proposal and submit.

### Medium-term (after first win)
6. **Activate Apify Upwork actor** — ~$10/month, handles the scraping without browser auth complexity. Revisit once first revenue lands.
7. **Raise prices and widen job criteria** — once JSS > 90% from 3 wins, open up to more complex jobs (£400-1,200 range).
8. **Submit the AI GTM Engineer proposal (EV 91.6)** — held in `/IntelForce/proposals/held/`. Release after 3 wins + positive JSS.

---

## 7. Key Decisions Made in This Session

| Decision | Rationale |
|----------|-----------|
| Cold-start strategy: Zapier/Make/n8n, £150-400, <15 proposals | Build JSS fast on easy wins before moving upmarket |
| Manual intake for discovery (no automation) | RSS deprecated, Brave needs CC, Google doesn't index Upwork |
| Human gate on all proposals and follow-ups | Upwork ToS — no auto-submit. Mani taps approve/reject per proposal |
| Proposal review format: EV score + title + budget + 3-sentence summary + Approve/Reject/Edit/Follow-Up | Approved by Mani during theta wave cycle 1 |
| Follow-up mechanic: T+24h draft, Send/Skip gate | Same human gate as proposals |
| JSS cold-start: price 20-30% below market on first 2-3 jobs | Standard Upwork cold-start playbook |
| GTM Engineer proposal (EV 91.6) held | Too complex for cold-start with 0 JSS |
| Portfolio penalty: -15 EV when no portfolio + job requests samples | Now lifted (portfolio_items=2) |
| Build order: discovery + proposal agents in parallel | No dependency between them |
| Speed weight: 0% (was 20%) | Manual intake means jobs always 60+ min old when scored — speed irrelevant |

---

## 8. Theta Wave Summary

The analyst runs theta-wave improvement cycles every 24h. Findings so far:

| Cycle | Score | Key Finding | Action Taken |
|-------|-------|-------------|--------------|
| 1 | 3/10 | Upwork account not live; build order confirmed | Account created, discovery agent spec approved |
| 2 | 4/10 | Portfolio gap is recurring blocker; catalog not yet created | Case studies written, portfolio penalty added to scoring model |
| 3 | 4/10 | System-ready, human-blocked (Mani offline 2 days); catalog still not created | n8n case study + profile draft written autonomously |

**Two-signal metrics established (tracking from today):**
- Signal 1: Hard filter pass rate (are qualifying jobs being submitted?)
- Signal 2: Go rate among passing jobs (is the scoring model calibrated?)

---

## 9. Scoring Model Reference

### EV Formula
```
skill_score = match % against our skill matrix (0-100)
win_probability = max(10, 95 - min(80, competition_count × 1.2))
speed_score = 90 if competition<=10 else 65 if competition<=30 else 40  [WEIGHT=0, manual intake mode]

ev = (0.80 × skill_score) + (0.20 × win_probability) + (0.00 × speed_score)
ev += budget_bonus + quality_bonus
ev = min(100, ev)
```

### Gate Thresholds
- EV >= 70 → REVIEW_AND_SEND (queue for human review)
- EV >= 82 + confidence >= 85 → AUTO_SEND_ELIGIBLE (disabled, gate_mode=manual)
- EV < 70 → HOLD

### Hard Filters (applied before EV scoring)
- Budget: £150-400 fixed price
- Competition: < 15 proposals
- Client: verified payment, spend history
- Keywords: Zapier, Make.com, or n8n (in job description)
- Red flags trigger automatic no-go

---

## 10. Useful Commands

```bash
# Run the pipeline manually (score + propose)
cd /Users/manidada/IntelForce
python3 scripts/revenue_pipeline.py --no-dry-run --gate-mode manual --limit 20

# Score a specific job from JSON
python3 scripts/job_scorer.py --json '{"title":"Zapier automation","required_skills":"zapier","proposals_count":8}'

# Check queue governance state
python3 scripts/queue_blocker_check.py

# Check what's in the proposals queue
ls proposals/pending/

# Test notification script
python3 scripts/notify_scored_jobs.py --dry-run

# cortextOS bus commands
cortextos bus send-telegram 8893758382 "<message>"
cortextos bus send-message analyst normal "<message>"
cortextos bus list-tasks --status pending
cortextos bus read-all-heartbeats
cortextos bus list-crons harry

# Check agent status
cortextos status
pm2 list
```

---

## 11. Files to Read for More Context

- `/Users/manidada/IntelForce/README.md` — full pipeline architecture
- `/Users/manidada/IntelForce/BUILD-COMPLETE.md` — what was pre-built and what's not done
- `/Users/manidada/IntelForce/JOB_CRITERIA.md` — scoring thresholds and red flags (current cold-start mode)
- `/Users/manidada/IntelForce/build-packs/catalog-listings-spec.md` — 3 catalog listing specs
- `/Users/manidada/IntelForce/build-packs/upwork-profile-draft.md` — profile copy to paste
- `/Users/manidada/IntelForce/research/upwork-cold-start-playbook.md` — cold-start research
- `/Users/manidada/cortextos/orgs/intel-force-engine/agents/harry/memory/2026-05-19.md` — day 1 session log
- `/Users/manidada/cortextos/orgs/intel-force-engine/agents/harry/memory/2026-05-20.md` — day 2 session log
- `/Users/manidada/cortextos/orgs/intel-force-engine/agents/harry/memory/2026-05-21.md` — today's session log
- `/Users/manidada/cortextos/orgs/intel-force-engine/agents/analyst/experiments/proposal-agent-spec.md` — approved proposal agent spec
- `/Users/manidada/cortextos/orgs/intel-force-engine/agents/analyst/experiments/discovery-agent-spec.md` — discovery agent spec

---

*End of session context document. Generated by harry (orchestrator).*

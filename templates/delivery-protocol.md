# Delivery Protocol

Every won job follows this protocol. No exceptions.

## Pre-Build: Intake Contract

Before writing a line of code, confirm all of these:

| Field | Required | Source |
|-------|----------|--------|
| Job URL + title | ✅ | Pipeline DB |
| Score + rationale | ✅ | Scoring output |
| Scope summary (deliverables, exclusions) | ✅ | Proposal promises |
| Budget type + timeline | ✅ | Job data |
| Competition snapshot | ✅ | Pipeline |
| Client risk profile | ✅ | Pipeline |
| Proposal promises made | ✅ | proposals/sent/ |

**If any field missing: do NOT start build. Get clarity first.**

Create build pack: `bash scripts/create_project.sh <job_id>`

---

## Phase A — Pre-commit (30–45 min)

1. Convert proposal claims → explicit acceptance criteria
2. Write scope lock:
   - In scope: [list exactly what will be delivered]
   - Out of scope: [list what is explicitly excluded]
   - Assumptions: [document all unknowns]
3. Define test plan and evidence format

---

## Phase B — Build (timeboxed milestones)

### Milestone 1: Foundation (25% budget)
- Set up project structure
- Get integrations/APIs authenticated
- Confirm data flows work end-to-end at basic level

### Milestone 2: Core logic (50% budget)
- Implement all primary functionality
- Error handling on happy path
- Internal testing passing

### Milestone 3: Polish + handoff (25% budget)
- Edge case handling
- Retry logic where appropriate
- Documentation and handoff assets

---

## Phase C — Stabilize

- [ ] Edge cases tested (empty inputs, nulls, unexpected data shapes)
- [ ] Failure paths tested (API down, timeout, auth failure, retry)
- [ ] Security: secrets in env vars, no hardcoded credentials, webhook validation
- [ ] Rate limiting respected
- [ ] Idempotency: running twice doesn't duplicate records

---

## Phase D — Client-Ready Handoff

Every delivery includes:
- `README.md` — setup and usage in plain English
- `docs/SETUP.md` — step-by-step install guide
- `docs/USER-GUIDE.md` — how to operate the system
- `docs/TESTING.md` — how to verify it's working
- `deliverables/TEST-REPORT.md` — what was tested and results
- `delivery-notes.md` — client-specific notes, assumptions, next steps

Optional (for complex projects):
- Loom walkthrough video
- `docs/DEPLOYMENT.md` — production deployment guide
- `docs/architecture.md` — system design overview

---

## Time Estimates

| Job Type | Minimum | Typical | Complex |
|----------|---------|---------|---------|
| Zapier/Make | 2h | 4h | 8h |
| n8n workflow | 4h | 8h | 16h |
| Simple chatbot | 4h | 8h | 16h |
| RAG chatbot | 8h | 16h | 32h |
| API integration | 4h | 8h | 20h |
| Web scraper | 2h | 4h | 10h |
| Discord/Slack bot | 4h | 8h | 16h |

Add **20% buffer** for: client communication, revisions, unexpected edge cases.

---

## QA Acceptance Checklist

- [ ] All promised deliverables shipped
- [ ] Scope creep blocked or documented as change request
- [ ] Deterministic test cases pass
- [ ] Failure modes tested and documented
- [ ] Client-operable documentation complete
- [ ] Handoff package assembled
- [ ] TEST-REPORT.md filled in with evidence

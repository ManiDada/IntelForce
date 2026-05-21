# Job Criteria

## Cold Start Phase (current mode)

This is the JSS-building strategy for the first 2-3 wins before moving upmarket. The goal is fast, easy closes on visual workflow tools (Zapier / Make.com / n8n) to build Job Success Score before targeting larger projects. All filters below apply in this mode.

## Must-Have Filters

| Criterion | Threshold |
|-----------|-----------|
| Platform focus | Zapier, Make.com, or n8n visual workflow builds ONLY |
| Budget | Fixed price £150–400 (NOT hourly, NOT large projects) |
| Complexity | Single clear deliverable — one automation, one workflow, one connection between two apps |
| Client | Verified payment method required, must have spend history (>0 spent) |
| Competition | Under 15 proposals (hard filter) |
| Brief clarity | Specific deliverable must be stated — no vague briefs |

## Sweet Spot

- Budget: £150–400 fixed price
- Type: Zapier / Make.com / n8n single-workflow build
- Complexity: simple — one automation, one integration, one clear output
- Client: verified payment, has prior spend, clear requirements
- Competition: <10 proposals ideal, hard cap at 15

## Automatic Red Flags (auto-reject regardless of score)

- "cheapest option" or "lowest price" language
- Vague fixed-price scope with no clear deliverables
- "Quick simple task" masking hidden complexity
- Client with dispute history or negative reviews
- Unrealistic timelines ("need it tomorrow" for 2-week project)
- "Equity only" or "revenue share only" payment
- New client with $0 spend and no verified payment
- Client location mismatch with payment currency (fraud signal)
- Contains: 'code', 'complex', 'multi-step', 'multiple integrations', 'various', 'etc'
- Budget outside £100–500 range
- No specific deliverable mentioned in the brief
- Requires custom code / scripting alongside the workflow tool
- 'several', 'many', 'full', 'custom code', 'development', 'build from scratch'

## Scoring Thresholds

| EV Score | Action |
|----------|--------|
| ≥82 + confidence ≥85 | Auto-send eligible (requires gate_mode=auto_high_conf, currently OFF) |
| ≥65 | Queue for human review (cold start threshold) |
| 55–64 | Generate proposal but flag medium confidence |
| <55 | Hold |

## Skill Confidence Caps

When job requires a skill below threshold, cap confidence and flag:

| Skill | Current Level | Max Confidence Without Warning |
|-------|---------------|-------------------------------|
| n8n | 40% | 65% |
| Make.com | 50% | 70% |
| HubSpot | 35% | 60% |
| Voice agents | 30% | 50% — decline if complex |
| RAG/LangChain | 65% | 80% |

## Competition Intelligence

| Proposals | Strategy |
|-----------|----------|
| <5 | Submit immediately if fit ≥70% |
| 5–10 | Submit with strong tailored opening |
| 10–15 | Only if strong skill match and differentiation (cold start hard cap) |
| 15+ | Skip — hard filter in cold start mode |
| 20–50 | Only if perfect fit and unique angle (post cold start) |
| 50+ | Skip unless exceptional match |

Client quality overrides competition count:
$300K+ client spend + 5 proposals > $10K client spend + 10 proposals

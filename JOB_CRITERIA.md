# Job Criteria

## Must-Have Filters

| Criterion | Threshold |
|-----------|-----------|
| Budget | £500+ (or $600+ USD) |
| Skill match | ≥70% |
| Timeline | Reasonable (not "in 24h for a 2-week job") |
| Client signals | No red flags |

## Sweet Spot

- Budget: £2,000–£10,000
- Type: automation / integration / workflow / AI agent
- Complexity: medium (not trivial, not 6-month enterprise)
- Client: verified, budget history, clear requirements

## Automatic Red Flags (auto-reject regardless of score)

- "cheapest option" or "lowest price" language
- Vague fixed-price scope with no clear deliverables
- "Quick simple task" masking hidden complexity
- Client with dispute history or negative reviews
- Unrealistic timelines ("need it tomorrow" for 2-week project)
- "Equity only" or "revenue share only" payment
- New client with $0 spend and no verified payment
- Client location mismatch with payment currency (fraud signal)

## Scoring Thresholds

| EV Score | Action |
|----------|--------|
| ≥82 + confidence ≥85 | Auto-send eligible (requires gate_mode=auto_high_conf, currently OFF) |
| ≥70 | Queue for human review |
| 60–69 | Generate proposal but flag medium confidence |
| <60 | Hold |

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
| 10–20 | Only if strong skill match and differentiation |
| 20–50 | Only if perfect fit and unique angle |
| 50+ | Skip unless exceptional match |

Client quality overrides competition count:
$300K+ client spend + 5 proposals > $10K client spend + 10 proposals

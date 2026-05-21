# Case Study: Real-Time CRM Event Routing with n8n

**Platform:** n8n (self-hosted)
**Industry:** B2B SaaS / Operations
**Time to build:** 2 hours
**Time saved per month:** ~10 hours
**Data stays:** on your infrastructure — no third-party SaaS required

---

## The Problem

A B2B SaaS company was using a CRM (Pipedrive) to manage their sales pipeline. Every time a deal moved to a new stage, two things needed to happen:

1. A row needed to be added to a Google Sheet that their ops team used for weekly revenue forecasting
2. A Slack message needed to go to the `#deals` channel so the wider team stayed informed in real time

The problem: neither of these happened automatically. A sales rep or admin had to manually copy deal details into the spreadsheet — and often forgot the Slack message entirely. By the end of the week, the forecast sheet was always 2–3 days behind, and the team had no live visibility into pipeline movement.

They had looked at Zapier and Make.com, but their technical lead wanted a solution that kept sensitive deal data on their own infrastructure rather than routing it through a US-hosted third-party service. n8n's self-hosted option was the answer.

---

## The Solution

An n8n workflow triggered by a Pipedrive webhook. Every time a deal stage changes, n8n fires instantly — appending a row to Google Sheets and posting a formatted Slack message — all within their own server environment, with zero data leaving their infrastructure.

**Trigger:** Pipedrive webhook (deal stage updated)
**Nodes:**
1. Receive and parse the webhook payload
2. Append a row to Google Sheets (deal name, value, new stage, owner, timestamp)
3. Post a formatted message to Slack `#deals`

---

## Workflow Nodes

**Node 1 — Webhook Trigger**
n8n exposes a unique webhook URL. This is registered in Pipedrive as an event subscription for "deal updated" events. When a deal stage changes, Pipedrive fires a POST to the webhook with the full deal payload — ID, name, value, current stage, owner, and timestamp. n8n receives it instantly with no polling latency.

**Node 2 — Google Sheets: Append Row**
The workflow extracts the relevant fields from the webhook payload and appends a new row to a "Pipeline Activity" Google Sheet. Columns written automatically: Deal Name, Deal Value (£), Previous Stage, New Stage, Owner, Date/Time. The sheet gives the ops team a running log of all stage changes — filterable by owner or stage, sortable by date — without anyone touching it manually.

**Node 3 — Slack: Post Message**
A formatted message posts to `#deals` immediately after the Sheets write completes. The message includes the deal name, new stage, value, and owner. Format is clean and scannable — the team sees pipeline movement as it happens, not in a Friday catch-up.

---

## What the Workflow Looks Like

*The n8n canvas shows three nodes in a horizontal chain: a green Webhook node on the left (showing the registered endpoint URL and a "Test" badge from the activation run), a Google Sheets node in the centre (with the "Append Row" operation selected and field mappings visible — deal_name mapped to column A, deal_value to column B, and so on), and a Slack node on the right (showing the formatted message template with n8n expression syntax pulling in deal_name, stage_name, and deal_value from the webhook payload). All three nodes display green success indicators from the test execution. The total canvas fits in a single screen — no scrolling required.*

---

## Result

| Metric | Before | After |
|--------|--------|-------|
| Time to update forecast sheet | Manual, 2–5 min per deal | 0 min — automatic |
| Ops sheet accuracy | 2–3 days behind | Real-time |
| Slack deal updates | Ad hoc, often missed | Every stage change, instantly |
| Monthly admin time | ~10 hrs | 0 hrs |
| Data infrastructure | Third-party SaaS routing | Self-hosted, no external data exposure |

The ops team's weekly forecast review went from "let me catch up the sheet first" to opening a live, accurate document. The sales team stopped getting asked "where is deal X up to?" because the answer was always in `#deals`.

---

## Why n8n Over Zapier or Make.com

For this client, the choice was straightforward: they wanted their CRM data to stay on their own servers. n8n's self-hosted option means the workflow runs on a VPS they control, with no data passing through Zapier's or Make.com's infrastructure. For a company handling enterprise deal values and client names, that matters.

The secondary benefit: n8n has no per-task pricing. Once deployed, this workflow can run thousands of times a month at zero marginal cost. At high pipeline volume, that makes it significantly cheaper than consumption-based tools.

---

## What I'd Do Differently at Scale

At higher deal volumes or with more complex routing logic (e.g. different Slack channels per deal owner, conditional notifications based on deal value), I'd add a Switch node after the webhook to branch the workflow based on deal properties before hitting Sheets and Slack. The current build is intentionally simple — one path, two outputs, zero branching — because that matched what this client needed. Complexity is added when there's a clear reason for it.

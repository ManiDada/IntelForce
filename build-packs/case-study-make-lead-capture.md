# Case Study: Eliminating Manual Lead Entry for a UK B2B Consulting Firm

**Platform:** Make.com (formerly Integromat)  
**Industry:** B2B Consulting  
**Time to build:** 3 hours  
**Time saved per month:** ~12 hours  
**Leads processed per month:** 50

---

## The Problem

A UK-based B2B consulting firm specialising in operational strategy was generating around 50 inbound leads per month through their website contact form. The process for handling each lead looked like this:

1. Someone on the team would see the form submission arrive in Gmail
2. They'd open a separate tab, log into Airtable, and manually add the lead — name, email, company, message, date, source
3. They'd switch to HubSpot and create a contact record, duplicating the same information
4. They'd go back to Gmail and write a personalised welcome email by hand

Each step took 4–6 minutes. Across 50 leads a month, that was 10–12 hours of repetitive data entry — done by senior consultants who billed at £150/hour. Leads that came in on Friday afternoons sometimes weren't followed up until Monday. Two leads in the previous quarter had gone cold because nobody had noticed the form submission.

The managing director's words: "We're a consulting firm. We should not be doing this by hand."

---

## The Solution

A Make.com scenario that intercepts every website form submission and handles the entire intake sequence automatically — Airtable logging, HubSpot contact creation, and personalised welcome email — in under 30 seconds of the lead hitting submit.

**Trigger:** New form submission (Typeform / website contact form via webhook)  
**Modules:**
1. Add lead to Airtable with timestamp, source tag, and initial status
2. Create contact in HubSpot CRM with all lead fields populated
3. Send personalised welcome email via Gmail using the lead's name and enquiry topic

No lead touches a human hand until it's already in the CRM, tagged, logged, and welcomed.

---

## Workflow Modules

**Module 1 — Trigger: Watch Form Submissions (Webhook)**  
Make.com listens for POST requests from the website contact form. The payload includes: first name, last name, email, company, message body, and UTM source parameter. Make.com parses this automatically — no custom code required.

**Module 2 — Airtable: Create a Record**  
A new row is created in the "Leads" table with the following fields populated automatically:
- Full Name, Email, Company
- Message (truncated to 500 chars to keep the table clean)
- Source (UTM parameter, defaults to "Direct" if absent)
- Lead Date (timestamp of submission)
- Status (defaulting to "New")
- Followed Up (checkbox, defaults to unchecked)

The Airtable view gives the team a live, filterable lead tracker with no manual input. Leads can be sorted by date, status, or source in one click.

**Module 3 — HubSpot: Create or Update Contact**  
Make.com checks HubSpot for an existing contact with the same email address. If found, it updates the record. If not, it creates a new contact with first name, last name, email, company, and a lead source property. This prevents duplicate contacts and keeps the CRM clean even if someone submits the form twice.

**Module 4 — Gmail: Send Personalised Welcome Email**  
An email is sent from the firm's Gmail account within seconds of form submission. The email uses the lead's first name in the greeting and references their enquiry topic (extracted from the message body). It confirms receipt, sets a response expectation ("we'll be in touch within one business day"), and includes a calendly link for those who want to book a call immediately.

The email is written in the firm's voice — warm, professional, not robotic. It reads like a human wrote it. Because the lead's name and topic are pulled directly from the form submission, every email is genuinely personalised, not mail-merge generic.

---

## What the Scenario Looks Like

*The Make.com canvas shows a horizontal flow of four modules connected by thin arrows: the Webhook trigger module on the left (showing a green "On" indicator), followed by the Airtable "Create a Record" module, then the HubSpot "Create/Update a Contact" module with a router to handle existing vs new contacts, and finally the Gmail "Send an Email" module on the right. Each module displays a run count in the bottom corner from the test execution. The router branching in the HubSpot step is the only complexity — the rest of the scenario is a straight line. Total modules: 5. Total development time from blank canvas to tested scenario: 3 hours.*

---

## Result

| Metric | Before | After |
|--------|--------|-------|
| Time per lead (admin) | 4–6 min | 0 min |
| Monthly admin hours | ~10–12 hrs | 0 hrs |
| Time to first contact | Up to 3 days | <30 seconds |
| Leads gone cold (prev. quarter) | 2 | 0 |
| Duplicate HubSpot contacts | Common | Eliminated |

The response time improvement was the biggest win. Leads now receive a personalised email within 30 seconds of submitting — before most competitors have even seen the enquiry. The managing director reported that two leads in the first month explicitly mentioned the speed of response as a reason they booked a call.

The firm also gained something they didn't expect: a clean, queryable lead database in Airtable that made their monthly pipeline review meetings significantly faster. Previously, those meetings relied on whoever had the best memory of recent leads.

---

## What I'd Do Differently at Scale

At 50 leads/month, this Make.com scenario runs on the Core plan (~£9/month). If lead volume grew substantially, I'd consider adding a scoring step — a simple filter module that routes high-priority leads (e.g. enterprise companies, specific job titles) to a separate Airtable view and triggers a Slack notification to the senior team in addition to the welcome email.

The current build is intentionally lean. Complexity is added when there's a clear reason for it, not in anticipation of problems that may never arrive.

---
name: ross-os-intel-summary
description: Add an intel block to the Morning Brief and generate weekly intel recaps with trends and recommended actions. Use this skill to synthesize Market Intel Events into actionable summaries.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-settings-io
---

# Ross OS — Intel Summary

## When to Use This Skill

Load this skill when:
- The Morning Brief needs the intel section
- Ross asks "what's happening in my space?" or "intel recap"
- Running the weekly intel recap (Sundays or Mondays)
- Ross wants trends analysis from accumulated intel

## Overview

Two modes:
1. **Daily (for Morning Brief):** Quick summary of new/unprocessed intel events
2. **Weekly recap:** Trend analysis across all intel from the past week

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Market Intel Events Table:** `grid-HEGLjzzMYd`
- **Contacts Table:** `grid-1M2UOaliIC`

## Instructions

### Mode 1: Daily Intel Block (for Morning Brief)

#### Fetch today's and untriaged intel

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for:
- `Status = New` (untriaged)
- OR `Signal date = today`

#### Compose daily intel block

```
## Intel Today

**[N] new signals** ([X] high priority)

### High Priority
- **[Person/Company]** — [Signal type]: [one-line summary]
  Action needed: [Yes/No — if Yes, what]

### Other Signals
- [Person] moved to [Role] at [Company] (job change)
- [Company] raised [Amount] Series [X] (funding)
- [Company] hiring [N] [roles] (hiring signal)

[N] events pending triage → run intel triage when ready
```

### Mode 2: Weekly Intel Recap

#### Fetch all intel from the past 7 days

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Signal date` within the last 7 days.

#### Analyze Trends

Group intel by:
1. **Signal type distribution** — How many job changes vs funding vs hiring?
2. **Company clustering** — Are multiple signals coming from the same companies?
3. **Role patterns** — What roles are moving? Is RevOps hiring up or down?
4. **Geographic patterns** — Any regional trends?
5. **Relationship to Ross's network** — How many signals involve known contacts?

#### Compose weekly recap

```
## Weekly Intel Recap — March 3-9, 2026

### Summary
- **[N] total signals** captured this week
- **[X] job changes**, [Y] funding events, [Z] hiring signals
- **[W] involved known contacts**
- **[V] outreach tasks created**

### Key Trends
1. **RevOps hiring surge at mid-market SaaS** — 5 companies posted VP+ RevOps roles this week. Market is hot for senior ops talent.
2. **Salesforce ecosystem funding** — 3 companies in the SF ecosystem raised rounds totaling $45M. Series A/B stage dominant.
3. **Contact network movement** — Jane Smith (VP RevOps → Acme), Mike Johnson (left CompanyX). 2 contacts changed roles.

### Notable Signals
| Signal | Person/Company | Details | Priority | Status |
|--------|---------------|---------|----------|--------|
| Job change | Jane Smith | VP RevOps at Acme Corp | High | Triaged — outreach pending |
| Funding | StartupX | Series B, $20M | Medium | Logged |
| Hiring | BigCorp | 5 RevOps roles posted | Medium | New |

### Recommended Actions
1. **Complete outreach to Jane Smith** — congrats on new role, high-value connection
2. **Monitor StartupX** — post-funding they may need RevOps help
3. **Consider BigCorp connection** — if they're hiring 5 RevOps people, someone in that team is worth knowing

### Pipeline Health
- Events this week: [N] (up/down from last week)
- Triage rate: [X]% processed
- Outreach conversion: [Y] tasks created from intel
- Pending: [Z] events still untriaged
```

## Integration with Morning Brief

When called from `ross-os-morning-brief`, return only the daily intel block (Mode 1). The parent skill will integrate it into the full briefing.

## Integration with Memory

After the weekly recap, store a memory entry:

```
"Ross OS: Weekly intel recap March 3-9. [N] signals, [X] job changes, [Y] funding. 
Key trend: [main trend]. [Z] outreach tasks. [W] still pending triage."
```

## Scheduling (Weekly Recap)

```
schedule_cron(
  action="create",
  name="Weekly Intel Recap",
  cron="0 14 * * 1",
  task="Load ross-os-intel-summary skill and generate the weekly intel recap.",
  background=false,
  exact=true
)
```

(Monday at 10am ET = 14:00 UTC)

## Error Handling

- No intel events → Report "No intel events this period"
- Too few events for trend analysis (< 5) → Skip trends section, just list events
- Intel events missing dates → Use created_at timestamp as fallback
- Weekly recap called mid-week → Adjust date range to cover since last recap

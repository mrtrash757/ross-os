---
name: ross-os-linkedin-intel
description: Monitor LinkedIn for role changes, hiring signals, and funding events relevant to Ross's ICP. Use this skill to track Salesforce/RevOps ecosystem moves, competitor hiring, and investment signals. Writes to Market Intel Events in Coda.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-coda-io ross-os-social-io ross-os-settings-io ross-os-supabase-io
---

# Ross OS — LinkedIn Intel Listener

## When to Use This Skill

Load this skill when:
- Scheduled intel check fires
- Ross says "check LinkedIn intel" or "any job changes?"
- Looking for outreach opportunities based on role changes
- Monitoring the Salesforce/RevOps/ICP ecosystem

## Overview

Focused on actionable business intelligence from LinkedIn:
- **Job changes** — people moving roles, especially into/out of ICP companies
- **Hiring signals** — companies posting RevOps/Salesforce roles
- **Funding events** — portfolio companies or targets raising rounds
- **Company news** — ICP company announcements

Unlike the general Social Listener, this skill is specifically optimized for LinkedIn professional signals.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Market Intel Events Table:** `grid-HEGLjzzMYd`
- **Contacts Table:** `grid-1M2UOaliIC`
- **Social Listening Rules Table:** `grid-LNI2nlJZ3X`
- **Supabase URL:** `https://fpuhaetqfohxtzhfrmpl.supabase.co`
- **Supabase Key:** `${SUPABASE_SERVICE_ROLE_KEY}`

## Instructions

### Step 1: Load Intel-Specific Rules

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LNI2nlJZ3X/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for rules where:
- `Active? = true`
- `Platform = LinkedIn` or `Platform = Both`
- `Type` contains intel-related categories (job_change, funding, hiring)

### Step 2: Execute LinkedIn Searches

Since LinkedIn doesn't have a public search API, use web search as proxy:

#### Job Changes
```
search_web(queries=[
  "site:linkedin.com 'new role' OR 'excited to announce' Salesforce RevOps 2026",
  "site:linkedin.com 'started a new position' RevOps OR 'Revenue Operations'"
])
```

#### Hiring Signals
```
search_web(queries=[
  "site:linkedin.com/jobs RevOps Salesforce hiring",
  "site:linkedin.com 'we're hiring' RevOps OR 'Revenue Operations'"
])
```

#### Funding Events
```
search_web(queries=[
  "'raised' OR 'funding round' Salesforce ecosystem 2026",
  "site:linkedin.com 'Series' OR 'seed round' RevOps"
])
```

#### Known Contact Monitoring
For high-importance contacts, check for activity:
```
search_web(queries=["site:linkedin.com/in/CONTACT_LI_SLUG recent activity"])
```

Also use X for LinkedIn-reported intel:
```
search_social(query="linkedin 'new role' Salesforce RevOps", only_recent=true, num_results=30)
```

### Step 3: Process and Classify Results

For each result, extract:

| Field | How to determine |
|-------|-----------------|
| Entity type | Person or Company |
| Person name | From post/profile |
| Old role/company | From "previously at" or context |
| New role/company | From announcement |
| Signal type | Job change / Funding / Hiring / Layoffs / Product launch |
| Relevance | High if ICP match, Medium if adjacent, Low if tangential |
| Priority | High if known contact or active deal, Medium otherwise |

### Step 4: Dedup Against Existing Intel

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Check for existing entries matching same Person + Signal type + similar date. Skip duplicates.

### Step 5: Write New Intel Events

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Jane Smith: VP RevOps at Acme Corp (was Sr Dir at OldCo)"},
        {"column": "Source platform", "value": "LinkedIn"},
        {"column": "Rule", "value": "RevOps job changes"},
        {"column": "Entity type", "value": "Person"},
        {"column": "Person name", "value": "Jane Smith"},
        {"column": "Person LI URL", "value": "https://linkedin.com/in/janesmith"},
        {"column": "Old role/company", "value": "Sr Director RevOps at OldCo"},
        {"column": "New role/company", "value": "VP RevOps at Acme Corp"},
        {"column": "Company name", "value": "Acme Corp"},
        {"column": "Signal type", "value": "Job change"},
        {"column": "Signal date", "value": "2026-03-08"},
        {"column": "Raw text / summary", "value": "LinkedIn post: Excited to share that I've joined Acme Corp as VP of Revenue Operations..."},
        {"column": "Relevance", "value": "High"},
        {"column": "Priority", "value": "High"},
        {"column": "Status", "value": "New"}
      ]
    }]
  }'
```

### Step 6: Cross-reference Contacts

Check if any intel person matches a known contact:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

If matched, set `Linked Contact` on the intel event. If the contact has Importance = High, bump the intel event to Priority = High.

### Step 7: Notify on High-Priority Intel

```
Title: "LinkedIn Intel: [N] new signals"
Body:
Job Changes: [X]
Funding: [Y]
Hiring: [Z]

Key signals:
- Jane Smith → VP RevOps at Acme Corp (known contact)
- Acme Corp raised Series B ($20M)
```

### Step 8: Log Completion

Log to Supabase agent_logs with counts.

## ICP Definition (for relevance scoring)

Ross's ICP for intel monitoring:
- **Roles:** RevOps, Sales Ops, Revenue Operations, Salesforce Admin, CRO, VP Sales
- **Companies:** Salesforce ecosystem companies, SaaS companies using Salesforce
- **Signals:** Job changes into VP+ roles, Series A-C funding, RevOps team expansions
- **Geography:** US-focused, with some attention to UK/EU

Score Relevance as:
- **High:** Known contact, ICP role at ICP company, or active deal connection
- **Medium:** ICP-adjacent role or company, interesting but not immediately actionable
- **Low:** Tangentially related, general industry noise

## Scheduling

Run alongside or slightly offset from the general Social Listener:

```
schedule_cron(
  action="create",
  name="LinkedIn Intel Listener",
  cron="0 */6 * * *",
  task="Load ross-os-linkedin-intel skill and execute it.",
  background=true,
  exact=false
)
```

## Error Handling

- Web search returns no results → Normal, report "No new signals found"
- Too many results → Prioritize by relevance, cap at 20 events per run
- Contact matching uncertain → Set Linked Contact to blank, note "Possible match: [name]" in Notes
- Rate limits → Process what you can, log partial results

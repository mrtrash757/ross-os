---
name: ross-os-social-listener
description: Run Social Listening Rules against X and LinkedIn feeds. Use this skill on a scheduled basis to monitor mentions, keywords, and signals defined in the Social Listening Rules table. Writes matches into Social Mentions Inbox and Market Intel Events in Coda.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-coda-io ross-os-social-io ross-os-settings-io ross-os-supabase-io
---

# Ross OS — Social Listener

## When to Use This Skill

Load this skill when:
- The social listener cron fires (every 4 hours per Settings)
- Ross says "check my mentions" or "run the social listener"
- Testing new listening rules

## Overview

Executes listening rules defined in Coda against X (via search_social) and LinkedIn (best-effort via web search). Writes matches to two tables:
- **Social Mentions Inbox** — mentions of Ross, his companies, or tracked keywords
- **Market Intel Events** — job changes, funding, hiring signals

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Social Listening Rules Table:** `grid-LNI2nlJZ3X`
- **Social Mentions Inbox Table:** `grid-LlvuOYy-3t`
- **Market Intel Events Table:** `grid-HEGLjzzMYd`
- **Contacts Table:** `grid-1M2UOaliIC`
- **Settings Table:** `grid-ybi2tIogls`
- **Supabase URL:** `https://fpuhaetqfohxtzhfrmpl.supabase.co`
- **Supabase Key:** `${SUPABASE_SERVICE_ROLE_KEY}`

## Instructions

### Step 0: Pre-flight

1. Load `ross-os-settings-io`. Check `social_listener_enabled`. If `false`, exit silently.
2. Log run start to Supabase `agent_logs`.

### Step 1: Load Active Listening Rules

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LNI2nlJZ3X/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Active? = true`. Each rule has:
- **Name:** Rule identifier
- **Platform:** X / LinkedIn / Both
- **Query:** Search query to execute
- **Category:** mentions / intel / competitor / keyword
- **Entity:** What/who to track
- **Signal:** What kind of signal to look for
- **Priority:** High / Medium / Low
- **Type:** mention / job_change / funding / hiring / product_launch

### Step 2: Execute Rules on X

For each X-platform rule, run:

```
search_social(
  query="{rule.Query}",
  num_results=20,
  only_recent=true
)
```

**Example queries from rules:**
- `@rossdimaio OR "Trash Panda Capital" OR "Asteria Air"` — brand mentions
- `"Salesforce" "RevOps" hiring` — industry intel
- `from:competitor_handle` — competitor monitoring

### Step 3: Execute Rules on LinkedIn

LinkedIn doesn't have a direct search API. Use web search as proxy:

```
search_web(queries=["site:linkedin.com {rule.Query}"])
```

Or for specific signals:
```
search_web(queries=["{rule.Entity} new role linkedin"])
```

This is best-effort. LinkedIn Intel Listener (#30) handles deeper LI monitoring.

### Step 4: Process Results

For each search result, classify:

#### Is this a Social Mention?
- Does it mention Ross, his companies, or his content?
- Is it a reply, quote, or direct mention?
→ Write to **Social Mentions Inbox**

#### Is this Market Intel?
- Job change, funding round, hiring signal, product launch?
- Does it relate to a tracked entity or ICP?
→ Write to **Market Intel Events**

#### Is this a duplicate?
Check existing entries in both tables before writing:

```bash
# Check recent mentions
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LlvuOYy-3t/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Match by: Author handle + Content similarity + Date proximity (same day).

### Step 5: Write Social Mentions

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LlvuOYy-3t/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Mention: @author on X re: Asteria Air"},
        {"column": "Platform", "value": "X"},
        {"column": "Author handle", "value": "@johndoe"},
        {"column": "Author type", "value": "Industry peer"},
        {"column": "Date", "value": "2026-03-08"},
        {"column": "Content", "value": "Full text of the mention"},
        {"column": "Link", "value": "https://x.com/johndoe/status/123456"},
        {"column": "Sentiment", "value": "Positive"},
        {"column": "Intent", "value": "Discussion"},
        {"column": "Priority", "value": "Medium"},
        {"column": "Status", "value": "New"},
        {"column": "Rule", "value": "Brand mentions"}
      ]
    }]
  }'
```

### Step 6: Write Market Intel Events

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Jane Smith moved to VP RevOps at Acme Corp"},
        {"column": "Source platform", "value": "LinkedIn"},
        {"column": "Rule", "value": "Salesforce RevOps job changes"},
        {"column": "Entity type", "value": "Person"},
        {"column": "Person name", "value": "Jane Smith"},
        {"column": "Person LI URL", "value": "https://linkedin.com/in/janesmith"},
        {"column": "Old role/company", "value": "Sr Director RevOps at OldCo"},
        {"column": "New role/company", "value": "VP RevOps at Acme Corp"},
        {"column": "Company name", "value": "Acme Corp"},
        {"column": "Signal type", "value": "Job change"},
        {"column": "Signal date", "value": "2026-03-08"},
        {"column": "Raw text / summary", "value": "Full post or announcement text"},
        {"column": "Relevance", "value": "High"},
        {"column": "Priority", "value": "High"},
        {"column": "Status", "value": "New"}
      ]
    }]
  }'
```

### Step 7: Contact Matching

For mentions and intel events, check if the person is a known contact:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

If matched, set `Related Contact` (mentions) or `Linked Contact` (intel).

### Step 8: Notify If High Priority

If any High-priority mentions or intel events were found:

```
Title: "Social Listener: [N] new items"
Body:
Mentions: [X] new ([Y] high priority)
Intel: [Z] new ([W] high priority)

Top items:
- [Mention/Intel summary]
- [Mention/Intel summary]
```

If no high-priority items, exit silently.

### Step 9: Log Completion

Log to Supabase with detail JSON including counts per rule, per type.

## Scheduling

```
schedule_cron(
  action="create",
  name="Social Listener",
  cron="0 */4 * * *",
  task="Load ross-os-social-listener skill and execute it.",
  background=true,
  exact=false
)
```

Per Settings: `social_listener_interval_hours = 4`

## Error Handling

- X search rate limited → Log, skip X rules, try LinkedIn rules
- No active rules → Exit silently, log "No active listening rules"
- Rule query too complex → Simplify and retry, log warning
- Coda rate limit → Batch writes, wait 10s between batches

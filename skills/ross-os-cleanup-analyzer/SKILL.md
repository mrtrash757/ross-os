---
name: ross-os-cleanup-analyzer
description: Apply Network Hygiene Rules to browsed data and write suggested cleanup actions to the Network Cleanup Queue in Coda. Use this skill to analyze LinkedIn connections, X posts, and other platform data against cleanup criteria.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-coda-io ross-os-headless-sandbox ross-os-settings-io ross-os-supabase-io
---

# Ross OS — Cleanup Analyzer

## When to Use This Skill

Load this skill when:
- Ross says "analyze my LinkedIn connections" or "what should I clean up?"
- Running a periodic hygiene check
- After the headless sandbox collects browsing data
- Ross uploads a LinkedIn connections export CSV

## Overview

Takes browsed or exported data from social platforms and applies the Network Hygiene Rules to identify items that should be flagged for cleanup. Writes suggestions to the Network Cleanup Queue with Status = New for Ross to review.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Network Hygiene Rules Table:** `grid-OR2yp9QHtp`
- **Network Cleanup Queue Table:** `grid-czCy9mvHAb`
- **Contacts Table:** `grid-1M2UOaliIC`
- **Interactions Table:** `grid-bDW7PytKOq`

## Instructions

### Step 1: Load Hygiene Rules

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-OR2yp9QHtp/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Active? = true`. Each rule defines:
- **Platform:** LinkedIn / X / Patreon / Google / Other
- **Object type:** Connection / Post / Message / Search result
- **Keep criteria:** What to keep (role, context, interaction recency)
- **Purge criteria:** What to purge (off-topic, dead connections, old cringe)
- **Action type:** Flag / Delete / Disconnect / Hide
- **Requires manual confirm?:** Usually Yes for destructive actions

### Step 2: Get Data to Analyze

#### Option A: From browsed data (headless sandbox output)

If the headless sandbox has already collected data, it will be saved in a workspace file. Read it:

```bash
cat /home/user/workspace/cleanup_data/{platform}_{timestamp}.json
```

#### Option B: From LinkedIn export CSV

Ross can export connections from LinkedIn Settings → Data Privacy → Get a copy of your data.

```bash
# Parse the connections CSV
python3 /home/user/workspace/parse_linkedin_export.py
```

#### Option C: Live browse (triggers headless sandbox)

If no existing data, load `ross-os-headless-sandbox` and browse.

### Step 3: Apply Rules

For each item in the data set, evaluate against all active rules for that platform:

#### LinkedIn Connections
```
For each connection:
  - Check Keep criteria:
    - Is their role relevant to Ross's work? (RevOps, SaaS, VC, founder)
    - Have they interacted recently? (check Interactions table)
    - Are they a known contact? (check Contacts table)
  - Check Purge criteria:
    - Off-topic role (e.g., real estate agent, fitness coach — unless personal)
    - No interaction in 2+ years
    - Dead account (no activity in 1+ year)
    - Connection was never meaningful (mass-connect from events)
  - If purge criteria match and keep criteria don't → Flag for disconnection
```

#### X Posts (monitor/flag only)
```
For each old post:
  - Check Purge criteria:
    - Old cringe content
    - Outdated opinions Ross no longer holds
    - Low engagement + low quality
    - Retweets of accounts now problematic
  - If purge criteria match → Flag for review (Ross uses Tweet Deleter for execution)
```

#### LinkedIn Posts
```
For each old post:
  - Check Purge criteria:
    - Content no longer represents Ross's current views
    - Low engagement + off-brand
    - From a company/role Ross is no longer associated with
  - If purge criteria match → Flag for deletion or hiding
```

### Step 4: Score and Prioritize

For each flagged item, score:

| Factor | Score |
|--------|-------|
| Clearly matches purge criteria | +3 |
| No keep criteria match | +2 |
| Old (2+ years) | +1 |
| Has keep criteria match | -3 |
| Recent interaction | -2 |
| Known contact | -5 (never auto-flag known contacts) |

Items with score >= 3 get written to the queue.

### Step 5: Write to Cleanup Queue

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-czCy9mvHAb/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Platform", "value": "LinkedIn"},
        {"column": "Object type", "value": "Connection"},
        {"column": "Identifier", "value": "https://linkedin.com/in/johndoe"},
        {"column": "Summary", "value": "John Doe — Real Estate Agent at XYZ Realty"},
        {"column": "Reason", "value": "Off-topic role, no interactions, connected 3 years ago at a random event"},
        {"column": "Proposed action", "value": "Disconnect"},
        {"column": "Status", "value": "New"}
      ]
    }]
  }'
```

Batch up to 10 rows per API call.

### Step 6: Present Analysis Summary

```
## Cleanup Analysis — LinkedIn Connections

**Analyzed:** 500 connections
**Flagged:** 47 for review

### Breakdown
- Disconnect recommended: 32
  - Off-topic roles: 18
  - Dead accounts: 9
  - Never meaningful: 5
- Hide posts: 8
- Flag for review (uncertain): 7

### Top Flags
1. John Doe — Real Estate Agent (off-topic, no interaction)
2. Jane's Old Account — No activity since 2023
3. [Post from 2022] — Outdated opinion about tool X
...

### Kept (453)
- 200+ in relevant roles (RevOps, SaaS, VC, founder)
- 150+ with recent interactions
- 100+ known contacts

Review the queue in Coda and approve/reject each item.
```

## Safety Rules

1. **Never auto-flag known contacts** — if someone is in the Contacts table, skip them
2. **Never flag high-importance contacts** — even if they match purge criteria
3. **Always write to queue first** — never skip the queue and go straight to execution
4. **Conservative scoring** — when in doubt, keep the connection
5. **Personal connections are exempt** — Ross may have non-business connections that matter

## Error Handling

- No data to analyze → Prompt Ross to export data or run a browse
- Hygiene rules empty → Report "No active hygiene rules defined — set them up in Coda"
- Queue write fails → Log error, save flagged items to workspace file as backup
- Contacts lookup fails → Skip contact-matching (conservative approach — may flag some known contacts)

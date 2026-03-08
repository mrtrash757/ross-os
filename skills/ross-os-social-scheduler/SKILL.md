---
name: ross-os-social-scheduler
description: Schedule social post drafts based on target frequencies from the Social Platforms table. Use this skill to assign Target dates to ready drafts, balance posting cadence across platforms, and surface today's social reps in the Morning Brief.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-settings-io
---

# Ross OS — Social Scheduling Helper

## When to Use This Skill

Load this skill when:
- Ross says "schedule my posts" or "plan my social for the week"
- Processing Social Post Drafts with Status = Ready that need Target dates
- The Morning Brief needs to surface "today's social reps"
- Reviewing posting cadence and suggesting adjustments

## Overview

This skill assigns publishing dates to ready drafts based on:
- Target frequencies per platform (from Social Platforms table)
- Max posts per day limits
- Existing scheduled posts (avoid double-booking)
- Optimal posting times per platform

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Social Post Drafts Table:** `grid-brOnpRoobl`
- **Social Platforms Table:** `grid-4VBVMRIw_-`

## Instructions

### Step 1: Load Platform Config

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-4VBVMRIw_-/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Extract per platform:
- `Target frequency` (e.g., "3x/week", "daily", "2x/week")
- `Max posts per day` (e.g., 2 for X, 1 for LinkedIn)

### Step 2: Load Current Schedule

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Build a calendar view:
- **Already scheduled:** Status = Ready/Draft with a Target date set
- **Published:** Status = Published with Actual post date
- **Unscheduled:** Status = Ready with no Target date

### Step 3: Calculate Scheduling Slots

For the next 7 days, determine available slots per platform:

```
For each platform:
  slots_per_day = Max posts per day (or 1 if not set)
  target_per_week = parse Target frequency
  
  For each day in next 7 days:
    existing = count of already-scheduled posts for this platform on this day
    available = slots_per_day - existing
    if available > 0: add to available_slots
```

### Step 4: Assign Dates to Unscheduled Drafts

For each unscheduled Ready draft:
1. Identify the platform
2. Find the next available slot for that platform
3. Spread posts evenly across the week (don't bunch up)
4. Respect max posts per day
5. Prioritize based on timeliness of the content

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "EXISTING_DRAFT_TITLE"},
        {"column": "Target date", "value": "2026-03-10"}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

### Step 5: Generate Schedule Summary

Produce a weekly view:

```
## Social Schedule — Week of March 9

**Monday 3/9**
- X: "Hot take about Salesforce pricing" (Ready)
- LinkedIn: "Three lessons from building Asteria Air" (Ready)

**Tuesday 3/10**
- X: "RevOps hiring is broken" (Draft — needs editing)

**Wednesday 3/11**
- (open slot — X)
- LinkedIn: "What nobody tells you about fundraising" (Ready)

**Thursday 3/12**
- X: "Thread on AI in RevOps" (Ready)

**Friday 3/13**
- (open slot — X)
- (open slot — LinkedIn)

**Pipeline:** 3 more ideas in Idea status, 2 in Draft
**Cadence check:** X on track (3/3 target), LinkedIn needs 1 more draft
```

### Step 6: Surface Today's Reps (for Morning Brief)

When called from Morning Brief, filter for:
```
Target date = today AND Status in [Ready, Draft]
```

Return formatted list:
```
## Today's Social Reps
- X: "Post title" (Status: Ready) — publish anytime
- LinkedIn: "Post title" (Status: Draft) — needs editing first
```

## Optimal Posting Times

Default recommendations (adjustable via Settings or performance data):

| Platform | Best Times (ET) | Best Days |
|----------|----------------|-----------|
| X | 8-10am, 12-1pm, 5-7pm | Mon-Fri |
| LinkedIn | 8-10am, 12pm | Tue-Thu |

These are starting defaults. The Performance Feedback skill (#27) will refine these based on actual engagement data.

## Scheduling Rules

1. **Never schedule more than `Max posts per day` per platform per day**
2. **Spread posts across the week** — don't schedule 5 X posts on Monday
3. **LinkedIn max 1/day** unless overridden — more than that hurts reach
4. **Time-sensitive content gets priority** — reactions, trending topics
5. **Weekends are optional** — only schedule if Ross's cadence includes weekends
6. **Don't auto-publish** — scheduling means setting Target date, not posting

## Error Handling

- No ready drafts → Report "Pipeline empty — run idea extraction and draft generation"
- Platform config missing frequencies → Use sensible defaults (X: 3x/week, LI: 2x/week)
- All slots full for the week → Report "Schedule is full, consider extending to next week"
- Conflict detected → Flag it, let Ross decide which post to move

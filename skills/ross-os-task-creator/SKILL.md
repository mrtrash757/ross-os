---
name: ross-os-task-creator
description: Create tasks in Ross OS from any context. Use this skill when an agent needs to create a task — routes to Personal Asteria Tasks in Coda for personal/sovereign tasks, Email-linked Tasks for email-originated tasks, or the Todoist Mirror for work tasks. Handles priority, due dates, contact linking, and source attribution.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-coda-io ross-os-settings-io
---

# Ross OS — Task Creator

## When to Use This Skill

Load this skill when:
- An agent needs to create a task from an email, mention, intel event, or conversation
- Ross says "add a task for..." or "remind me to..."
- The Email Monitor classifies an email as needing a task
- The Fire Scan or Stale Radar surfaces something that needs a task
- Any workflow produces an action item

## Task Routing Logic

Ross OS has three task tables. Route based on context:

| Source | Destination Table | Table ID |
|--------|-------------------|----------|
| Personal / sovereign tasks | Personal Asteria Tasks | `grid-G1O2W471aC` |
| Email-originated tasks | Email-linked Tasks | `grid-7IWNsZiHzE` |
| Work tasks (rare — usually Todoist) | Todoist Mirror (read-only) | `grid--YZeFkNofZ` |

**Decision tree:**
1. Did this come from an email? → **Email-linked Tasks**
2. Is this a personal/Asteria/sovereign task? → **Personal Asteria Tasks**
3. Is this a work task Ross would manage in Todoist? → Tell Ross to add it in Todoist (mirror is read-only from Coda side)

## Credentials

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Base URL:** `https://coda.io/apis/v1/docs/nSMMjxb_b2`

## Instructions

### Creating a Personal Asteria Task

**Table:** `grid-G1O2W471aC`

**Columns:**
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| Name | text | Yes | Task title — clear, actionable |
| Status | text | No | Default: blank (means "To Do"). Options: In Progress, Done, Dropped |
| Due date | date | No | ISO format: 2026-03-10 |
| Priority | text | No | Critical, High, Medium, Low |
| Notes | text | No | Additional context |
| Context | text | No | Where this came from (e.g., "Email from Jane", "Morning Brief", "Fire Scan") |
| Source | text | No | Agent skill that created it (e.g., "email-monitor", "fire-scan") |
| Linked Contact | text | No | Contact name (must match a row in Contacts table) |

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Follow up with Jane on Asteria Air term sheet"},
        {"column": "Due date", "value": "2026-03-10"},
        {"column": "Priority", "value": "High"},
        {"column": "Context", "value": "Email from Jane Chen re: term sheet review"},
        {"column": "Source", "value": "email-monitor"},
        {"column": "Linked Contact", "value": "Jane Chen"}
      ]
    }]
  }'
```

### Creating an Email-linked Task

**Table:** `grid-7IWNsZiHzE`

**Columns:**
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| Name | text | Yes | Task title |
| Source | text | No | "Gmail" or email account label |
| Due date | date | No | ISO format |
| Notes | text | No | Email summary or context |
| Status | text | No | Default blank. Options: Done, Dropped |
| Context | text | No | Classification context from email monitor |
| Email account | text | No | "ross@trashpanda.capital" |
| Thread ID link | text | No | Gmail thread URL for quick reference |
| Contact | text | No | Sender name |

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Reply to investor update request from Mark"},
        {"column": "Source", "value": "Gmail"},
        {"column": "Due date", "value": "2026-03-09"},
        {"column": "Notes", "value": "Mark asked for Q1 investor update deck. Need to send by EOW."},
        {"column": "Context", "value": "Classified as: action-required, priority: high"},
        {"column": "Email account", "value": "ross@trashpanda.capital"},
        {"column": "Thread ID link", "value": "https://mail.google.com/mail/u/0/#inbox/THREAD_ID"},
        {"column": "Contact", "value": "Mark Thompson"}
      ]
    }]
  }'
```

### Suggesting a Todoist Task (work context)

Since the Todoist Mirror is read-only from the Coda side (synced via Simpladocs pack), you cannot create Todoist tasks via the Coda API. Instead:

1. Tell Ross: "This looks like a work task — I'd suggest adding it to Todoist: [task description]"
2. If Ross confirms, create it as a Personal Asteria Task with a note saying "Consider moving to Todoist"
3. Or if a Todoist connector becomes available in the future, use it directly

## Task Quality Standards

When creating tasks from automated sources (email monitor, fire scan, etc.):

1. **Name must be actionable** — start with a verb: "Reply to...", "Review...", "Follow up with...", "Schedule..."
2. **Always set Context** — the user needs to know WHY this task exists
3. **Always set Source** — which agent/skill created it
4. **Set Priority based on signals:**
   - Critical: deadline today, money on the line, blocking others
   - High: deadline this week, important relationship, time-sensitive
   - Medium: should do soon, no hard deadline
   - Low: nice to do, informational
5. **Set Due date when inferrable** — from email content, deadline mentions, or default to tomorrow for action-required items
6. **Link contacts when possible** — if the task relates to a known contact, link it

## Deduplication

Before creating a task, check if a similar one already exists:

```bash
# Check Personal Asteria Tasks for duplicates
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows?useColumnNames=true&query=Name:follow%20up%20Jane" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

If a similar task exists with Status not Done/Dropped, skip creation and note it in the log.

## Bulk Task Creation

For multiple tasks (e.g., from processing several emails):

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [
      {
        "cells": [
          {"column": "Name", "value": "Task 1"},
          {"column": "Priority", "value": "High"},
          {"column": "Source", "value": "email-monitor"}
        ]
      },
      {
        "cells": [
          {"column": "Name", "value": "Task 2"},
          {"column": "Priority", "value": "Medium"},
          {"column": "Source", "value": "email-monitor"}
        ]
      }
    ]
  }'
```

Batch up to 10 tasks per API call to stay within rate limits.

## Error Handling

- If Coda API returns 429, wait 10 seconds and retry once
- If Coda API returns 400, log the error and the payload for debugging
- Never silently fail — always log the task creation attempt and result
- If dedup check fails (API error), create the task anyway (better a duplicate than a missed task)

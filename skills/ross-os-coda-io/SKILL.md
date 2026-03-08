---
name: ross-os-coda-io
description: Read and write data in the Ross OS Coda doc. Use this skill whenever you need to access Ross's personal operating system — tasks, contacts, habits, workouts, social drafts, intel events, or any of the 21 tables in the Ross OS Coda doc. Provides table IDs, column mappings, and API patterns.
metadata:
  author: ross-os
  version: '1.0'
  category: io
---

# Ross OS — Coda IO Skill

## When to Use This Skill

Load this skill when you need to:
- Read or write data in any Ross OS Coda table
- Look up table IDs or column names
- Create, update, or query rows
- Build other Ross OS skills that depend on Coda data

## Credentials

- **Doc ID:** `nSMMjxb_b2`
- **API Token:** `${CODA_API_TOKEN}` (scoped to this doc only)
- **Base URL:** `https://coda.io/apis/v1/docs/nSMMjxb_b2`
- **Doc URL:** https://coda.io/d/_dnSMMjxb_b2/RossOS_suRY7HB2

## API Patterns

All calls use `curl` or `fetch` with the auth header:
```
Authorization: Bearer ${CODA_API_TOKEN}
```

### List rows (with column names)
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/{TABLE_ID}/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Get a single row
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/{TABLE_ID}/rows/{ROW_ID}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Upsert rows (create or update)
```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/{TABLE_ID}/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [
      {
        "cells": [
          {"column": "Column Name", "value": "the value"}
        ]
      }
    ],
    "keyColumns": ["Column Name"]
  }'
```
Use `keyColumns` for upsert behavior (match on that column, update if exists, create if not).

### Filter rows
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/{TABLE_ID}/rows?useColumnNames=true&query=ColumnName:value" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Delete a row
```bash
curl -s -X DELETE "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/{TABLE_ID}/rows/{ROW_ID}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

## Rate Limits
- Coda API: ~10 requests/6 seconds for doc-scoped tokens
- If you hit 429, wait 10 seconds and retry
- For bulk operations, batch rows in a single upsert call (up to 500 rows)

## Table Registry

### Core Ops

#### Days
ID: `grid-Zm8ylxf9zc`
Spine of the system. Every daily view links here.

| Column | Type |
|--------|------|
| Date | date |
| Start of day intent | text |
| End of day summary | text |
| Sleep | text |
| Energy | select |
| Workout Instances | lookup |
| Habit Logs | lookup |
| Personal Asteria Tasks | lookup |
| Email-linked Tasks | lookup |
| Interactions | lookup |
| Meetings Events | lookup |
| Stale contacts | lookup |
| Social posts today | lookup |
| Intel events today | lookup |

#### Workouts (definitions)
ID: `grid-kOoUMffFTS`

| Column | Type |
|--------|------|
| Name | text |
| Category | select |
| Body focus | text |
| Default days | select |
| Program / Phase | text |
| Notes | text |

#### Workout Instances (executions)
ID: `grid-vEv0-YZI9h`

| Column | Type |
|--------|------|
| Name | text |
| Workout | lookup |
| Date | date |
| Notes | canvas |
| Days | lookup |
| Planned start time | time |
| Completed? | checkbox |
| Weight/reps/distance | text |
| Duration | text |

#### Habits (definitions)
ID: `grid-5WHcBsnbmk`

| Column | Type |
|--------|------|
| Name | text |
| Category | select |
| Frequency | select |
| Target count | number |
| Active? | checkbox |

#### Habit Logs (daily status)
ID: `grid-5FJBmY91ko`

| Column | Type |
|--------|------|
| Name | text |
| Habit | text |
| Date | text |
| Notes | canvas |
| Completed? | checkbox |
| Day | lookup |
| Count | number |
| Streak | number |

### Tasks

#### Personal Asteria Tasks
ID: `grid-G1O2W471aC`
System of record for non-work tasks.

| Column | Type |
|--------|------|
| Name | text |
| Status | select (New / In progress / Waiting / Done / Dropped) |
| Due date | date |
| Notes | canvas |
| Context | select (Personal / Asteria Air / Asteria Partners / TPC) |
| Source | select (Manual / Email / Recurring / Bot suggestion / Social / Intel) |
| Day | lookup |
| Priority | select (Low / Medium / High / Critical) |
| Linked Contact | lookup |
| Created at | date |
| Completed at | date |

#### Email-linked Tasks
ID: `grid-7IWNsZiHzE`

| Column | Type |
|--------|------|
| Name | text |
| Source | text |
| Due date | text |
| Notes | canvas |
| Status | select |
| Context | select |
| Day | lookup |
| Email account | text |
| Thread ID link | link |
| Contact | lookup |

#### Todoist Mirror (work tasks — read only)
ID: `grid--YZeFkNofZ`
Populated by Simpladocs Todoist Pack. Do not write to this table.

| Column | Type |
|--------|------|
| Name | text |
| Project | text |
| Due date | date |
| Done? | checkbox |
| Priority | select |
| Labels | text |
| Status | select |
| Is today? | checkbox |
| Todoist URL | link |

**Note:** The Simpladocs pack also created sync tables `grid-sync-48345-Task` and `grid-sync-48345-Project` with richer data (Content, Description, Project, Labels, Priority, Due date, Checked, Task id, Task link, etc). Prefer those for reading live Todoist data.

#### Calendar Mirror
ID: `grid-KqCsJ3ILm9`

| Column | Type |
|--------|------|
| Name | text |
| Calendar | text |
| Date | text |
| Start time | time |
| End time | time |
| Location | text |
| Days | lookup |

### CRM

#### Contacts
ID: `grid-1M2UOaliIC`

| Column | Type |
|--------|------|
| Name | text |
| Org | text |
| Role | text |
| Notes | text |
| Context tags | select (Family / Operator / Investor / Ally / Threat / Other) |
| Channels | select (LI / X / Text / Email / In-person) |
| Importance | select (Low / Med / High) |
| Cadence | number (days) |
| Last interaction date | date |
| LinkedIn URL | link |
| Next touch date | date |

#### Interactions
ID: `grid-bDW7PytKOq`

| Column | Type |
|--------|------|
| Contact | lookup |
| Date | date |
| Channel | select (LI / X / Text / Email / Call / In-person / Other) |
| Notes | canvas |
| Type | select (Intro / Check-in / Deal / Deep / Personal / Other) |
| Related Day | lookup |

#### Meetings & Events
ID: `grid-HRBNYX_9N1`

| Column | Type |
|--------|------|
| Title | text |
| Day | lookup |
| Start time | text |
| Date | date |
| End time | text |
| Type | select (Work / Asteria / Personal) |
| Location Link | link |
| Related Contacts | lookup |

### Social Output

#### Social Platforms
ID: `grid-4VBVMRIw_-`

| Column | Type |
|--------|------|
| Name | text |
| Voice profile | text |
| Target frequency | number (posts/week) |
| Max posts per day | number |

#### Social Themes
ID: `grid-3IQP9JSQGw`

| Column | Type |
|--------|------|
| Name | text |
| Platform | select |
| Description | text |
| Example post links | link |
| Primary platform | select (X / LI / Both) |

#### Social Post Drafts
ID: `grid-brOnpRoobl`

| Column | Type |
|--------|------|
| Name | text |
| Platform | lookup |
| Theme | lookup |
| Status | select (Idea / Draft / Ready / Posted / Killed) |
| Core idea | text |
| X draft | text |
| LinkedIn draft | text |
| Target date | date |
| Actual post date | date |
| Link to live post | link |
| Created via | select (Manual / Bot suggestion) |
| Performance | text |

### Social Listening & Intel

#### Social Listening Rules
ID: `grid-LNI2nlJZ3X`

| Column | Type |
|--------|------|
| Name | text |
| Platform | select (X / LinkedIn) |
| Query | text |
| Active? | checkbox |
| Frequency | select |
| Category | select (Personal brand / Asteria brand / Market intel) |
| Entity | select (Person / Company / Topic) |
| Signal | select (Mention / Job change / Funding / Hiring / Other) |
| Priority | select (High / Medium / Low) |
| Type | select (Mention / Keyword / Handle / List) |

#### Social Mentions Inbox
ID: `grid-LlvuOYy-3t`

| Column | Type |
|--------|------|
| Name | text |
| Platform | select |
| Author handle | text |
| Rule | lookup |
| Author type | select (Operator / Investor / Media / Rando / Unknown) |
| Date | date |
| Content | text |
| Link | link |
| Sentiment | select (Positive / Neutral / Negative) |
| Intent | select (Opportunity / Threat / Question / FYI / Spam) |
| Priority | select (High / Medium / Low) |
| Status | select (New / Triaged / Replied / Logged / Ignored) |
| Related Contact | lookup |
| Creates Task? | checkbox |
| Linked Task | lookup |

#### Market Intel Events
ID: `grid-HEGLjzzMYd`

| Column | Type |
|--------|------|
| Name | text |
| Source platform | select (LinkedIn / X / Other) |
| Rule | lookup |
| Entity type | select (Person / Company) |
| Person name | text |
| Person LI URL | link |
| Old role/company | text |
| New role/company | text |
| Company name | text |
| Signal type | select (Job change / Funding / Hiring / Layoffs / Product launch / Other) |
| Signal date | date |
| Raw text / summary | text |
| Relevance | select (High / Medium / Low) |
| Priority | select (High / Medium / Low) |
| Status | select (New / Triaged / Logged / Actioned / Ignored) |
| Linked Contact | lookup |
| Linked Task | lookup |

#### Hivekiln Import Staging
ID: `grid-TAFYZLAB9W`

| Column | Type |
|--------|------|
| Name | text |
| HK Workouts raw | text |
| HK Tasks raw | text |

### Hygiene & Cleanup

#### Network Hygiene Rules
ID: `grid-OR2yp9QHtp`

| Column | Type |
|--------|------|
| Name | text |
| Rule type | select |
| Trigger | text |
| Frequency | select |
| Platform | select (LinkedIn / X / Patreon / Google / Other) |
| Object type | select (Connection / Post / Message / Search result) |
| Keep criteria | text |
| Purge criteria | text |
| Action type | select (Flag / Delete / Disconnect / Hide) |
| Requires manual confirm? | checkbox |
| Active? | checkbox |

#### Network Cleanup Queue
ID: `grid-czCy9mvHAb`

| Column | Type |
|--------|------|
| Platform | select |
| Object type | select |
| Identifier | link (URL or ID) |
| Summary | text |
| Reason | text |
| Proposed action | select |
| Status | select (New / Approved / Rejected / Executed) |

## Common Recipes

### Get today's Day row
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-Zm8ylxf9zc/rows?useColumnNames=true&query=Date:$(date +%Y-%m-%d)" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Get open tasks (Status != Done, != Dropped)
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```
Then filter client-side for Status not in [Done, Dropped].

### Get stale contacts (high importance, overdue cadence)
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```
Then filter where Importance = High and Next touch date <= today.

### Create a new task
```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Follow up with Jane"},
        {"column": "Context", "value": "Asteria Air"},
        {"column": "Source", "value": "Bot suggestion"},
        {"column": "Status", "value": "New"},
        {"column": "Priority", "value": "High"},
        {"column": "Due date", "value": "2026-03-10"}
      ]
    }]
  }'
```

### Log an interaction
```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-bDW7PytKOq/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Contact", "value": "Jane Smith"},
        {"column": "Date", "value": "2026-03-08"},
        {"column": "Channel", "value": "Email"},
        {"column": "Type", "value": "Check-in"},
        {"column": "Notes", "value": "Discussed Q2 plans"}
      ]
    }]
  }'
```

## Error Handling

- **401:** Token expired or invalid. Alert Ross.
- **404:** Table or row not found. Check table ID against registry above.
- **429:** Rate limited. Wait 10 seconds, retry. Max 3 retries.
- **500:** Coda server error. Wait 30 seconds, retry once.
- On any persistent failure, log the error and notify Ross rather than silently failing.

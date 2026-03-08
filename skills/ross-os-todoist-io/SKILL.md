---
name: ross-os-todoist-io
description: Read Todoist task data from the Ross OS Coda doc. Use this skill when you need to check work tasks, project status, or what's due today from Todoist. Data flows via the Simpladocs Todoist Pack into Coda sync tables — this skill reads those tables. No direct Todoist API needed.
metadata:
  author: ross-os
  version: '1.0'
  category: io
---

# Ross OS — Todoist IO Skill

## When to Use This Skill

Load this skill when you need to:
- Check Ross's work tasks from Todoist
- See what's due today or overdue
- Look up tasks by project (Pipeline, Outreach, Internal Projects, Inbox)
- Read task priority, labels, or completion status
- Cross-reference Todoist tasks with the Day view

## Architecture

Todoist data flows into Coda via the **Simpladocs Todoist Pack** (installed in the Ross OS doc). There is no direct Todoist API integration — the pack handles the sync automatically.

Two data sources in Coda:

1. **Todoist Mirror** (`grid--YZeFkNofZ`) — Curated view with key columns. Read-only.
2. **Simpladocs Sync Tables** — Raw pack data with richer fields:
   - Tasks: `grid-sync-48345-Task`
   - Projects: `grid-sync-48345-Project`

Prefer the sync tables for live data; use Todoist Mirror for the simplified view.

## Credentials

Uses the Coda API (same as ross-os-coda-io):
- **Doc ID:** `nSMMjxb_b2`
- **API Token:** `${CODA_API_TOKEN}`
- **Base URL:** `https://coda.io/apis/v1/docs/nSMMjxb_b2`

## Reading Tasks

### Get all Todoist tasks (from sync table)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-sync-48345-Task/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

**Sync table columns:** Content, Description, Project, Labels, Priority, Due date, Checked, Task id, Task link

### Get all projects

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-sync-48345-Project/rows?useColumnNames=true&limit=50" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Get Todoist Mirror (curated view)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid--YZeFkNofZ/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

**Mirror columns:** Name, Project, Due date, Done?, Priority, Labels, Status, Is today?, Todoist URL

## Common Recipes

### Get tasks due today

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid--YZeFkNofZ/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Then filter client-side: `Is today? == true` or `Due date == today's date`.

### Get open tasks by project

Fetch all tasks, then filter client-side where `Done? != true` and `Project == "Pipeline"` (or Outreach, Internal Projects, Inbox).

### Get high-priority tasks

Fetch all tasks, then filter where `Priority` is p1 or p2 (Todoist uses p1=urgent, p2=high, p3=medium, p4=low).

## Important Notes

- **Read-only:** Do not write to these tables. The Simpladocs pack owns the sync.
- **Sync frequency:** The pack syncs automatically. Data may lag by a few minutes.
- **Creating Todoist tasks:** Use the Todoist app or API directly (not yet integrated). Or create tasks in the Personal Asteria Tasks table in Coda if they're personal/Asteria tasks.
- **48 tasks** across 4 projects were synced at setup time.

## Error Handling

- **401:** Coda API token expired. Alert Ross.
- **404:** Table not found. Verify table ID hasn't changed after pack reinstall.
- **429:** Rate limited. Wait 10 seconds, retry.
- **Empty results:** The pack may need a manual sync trigger in Coda.

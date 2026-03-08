---
name: ross-os-morning-brief
description: Generate Ross's cross-stack morning briefing. Use this skill every morning (6:30am ET via schedule) or when Ross asks for his morning brief, daily summary, or what's on his plate today. Pulls from calendar, tasks, contacts, habits, social, and intel to produce one cohesive briefing.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-todoist-io ross-os-calendar-io ross-os-email-io ross-os-supabase-io
---

# Ross OS — Morning Brief

## When to Use This Skill

Load this skill when:
- The morning cron fires (6:30am ET daily)
- Ross asks "what's my day look like?" or "morning brief" or "what's on my plate"
- Ross wants a summary of what's happening today

## Instructions

Execute these steps in order. Load IO skills as needed.

### Step 1: Log the run (start)

Load `ross-os-supabase-io`. Insert an agent_logs row:

```bash
SUPABASE_URL="https://fpuhaetqfohxtzhfrmpl.supabase.co"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"

curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"skill_name": "morning-brief", "triggered_by": "schedule", "status": "running"}]'
```

Save the returned `id` as `LOG_ID`.

### Step 2: Get today's date context

```bash
TODAY=$(date +%Y-%m-%d)
DOW=$(date +%A)
```

### Step 3: Fetch calendar (what meetings today?)

Load `ross-os-calendar-io`. Search for today's events:

```json
{
  "tool_name": "search_calendar",
  "source_id": "gcal",
  "arguments": {
    "start_date": "{TODAY}T00:00:00-04:00",
    "end_date": "{TODAY}T23:59:59-04:00",
    "queries": [""]
  }
}
```

Collect: meeting count, first meeting time, meeting list with titles/times/attendees.

### Step 4: Fetch tasks due today

Load `ross-os-coda-io`. Get Personal Asteria Tasks:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter client-side:
- Status NOT in [Done, Dropped]
- Due date == today OR overdue (Due date < today)
- Sort by Priority (Critical > High > Medium > Low)

Load `ross-os-todoist-io`. Get work tasks:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid--YZeFkNofZ/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Is today? == true` or `Due date == today` and `Done? != true`.

### Step 5: Check habits

Get active habits and today's logs:

```bash
# Active habits
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-5WHcBsnbmk/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"

# Today's habit logs
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-5FJBmY91ko/rows?useColumnNames=true&query=Date:{TODAY}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Report: which habits are tracked, any streaks to maintain.

### Step 6: Check stale contacts (quick scan)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter where:
- Importance == "High"
- Next touch date <= today
- Count them. If > 0, flag in brief.

### Step 7: Check social mentions (new/untriaged)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LlvuOYy-3t/rows?useColumnNames=true&query=Status:New" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Count new mentions. Flag high-priority ones.

### Step 8: Check intel events (new)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows?useColumnNames=true&query=Status:New" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Count new intel events. Flag high-relevance ones.

### Step 9: Compose the brief

Format the briefing as a clean, scannable summary:

```
## Morning Brief — {DOW}, {TODAY}

### Schedule ({meeting_count} meetings)
- 9:00am — Team Standup (30min)
- 11:00am — Coffee with Jane (Asteria Air)
- 2:00pm — Board prep (1hr)
First meeting at {first_meeting_time}.

### Tasks Due ({task_count})
**Critical/High:**
- [ ] Follow up with Jane re: Asteria Air (High, Asteria Air)
- [ ] Review term sheet (Critical, Asteria Partners)

**Work (Todoist):**
- [ ] Pipeline: Call investor X (p1)
- [ ] Internal: Update deck (p2)

**Overdue ({overdue_count}):**
- [ ] Send tax docs — was due Mar 5

### Habits
Active streaks: Workout (5 days), Reading (12 days)
Today's habits: Workout, Meditate, Read, Journal

### Network
{stale_count} contacts overdue for a touch (High importance)

### Social & Intel
{mention_count} new social mentions ({high_priority_count} high priority)
{intel_count} new intel events

### Energy Check
Remember to log: Sleep, Energy level, Start of day intent
```

### Step 10: Deliver the brief

- **If triggered by cron:** Send as notification via `send_notification`
- **If triggered manually:** Return as the response to Ross

### Step 11: Write to Day row

Upsert today's Day row with the start-of-day intent if Ross provides one:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-Zm8ylxf9zc/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{"cells": [{"column": "Date", "value": "{TODAY}"}]}],
    "keyColumns": ["Date"]
  }'
```

### Step 12: Log the run (complete)

```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_logs?id=eq.{LOG_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "completed_at": "{NOW_UTC}",
    "status": "success",
    "summary": "{meeting_count} meetings, {task_count} tasks, {stale_count} stale contacts, {mention_count} mentions",
    "detail": {
      "meetings": {meeting_count},
      "tasks_due": {task_count},
      "tasks_overdue": {overdue_count},
      "stale_contacts": {stale_count},
      "new_mentions": {mention_count},
      "new_intel": {intel_count}
    }
  }'
```

### Step 13: Store memory

After completion, store a memory entry:

```
"Ross OS: Ran morning-brief at {TODAY} {TIME}. 
{meeting_count} meetings, {task_count} tasks due ({overdue_count} overdue), 
{stale_count} stale contacts, {mention_count} new mentions, {intel_count} intel events."
```

## Error Handling

- If any IO step fails, continue with remaining steps. Report partial data.
- Log with `status: partial` if some sections couldn't be fetched.
- Log with `status: error` only if the entire brief fails.
- If Coda returns 429, wait 10s and retry (max 3 retries per call).
- Always deliver whatever data was collected — a partial brief is better than none.

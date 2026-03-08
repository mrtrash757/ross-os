---
name: ross-os-eod-debrief
description: Generate Ross's end-of-day debrief and log the day's data. Use this skill at end of day (11pm ET via schedule) or when Ross asks for his EOD summary, daily recap, or to close out the day. Summarizes what happened, logs completions, and preps for tomorrow.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-supabase-io
---

# Ross OS — EOD Debrief

## When to Use This Skill

Load this skill when:
- The EOD cron fires (11pm ET daily)
- Ross asks "close out my day" or "EOD summary" or "what did I do today"
- Ross wants to review and log the day

## Instructions

### Step 1: Log the run (start)

```bash
SUPABASE_URL="https://fpuhaetqfohxtzhfrmpl.supabase.co"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"

curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"skill_name": "eod-debrief", "triggered_by": "schedule", "status": "running"}]'
```

Save `LOG_ID`.

### Step 2: Get today's data

```bash
TODAY=$(date +%Y-%m-%d)
```

Load `ross-os-coda-io`.

#### Tasks completed today

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter: `Status == "Done"` AND `Completed at == today`. Count them.
Also count: tasks still open with today's due date (carried over).

#### Work tasks completed (Todoist)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid--YZeFkNofZ/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter: `Done? == true` from today's tasks.

#### Habits logged today

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-5FJBmY91ko/rows?useColumnNames=true&query=Date:{TODAY}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Count completed vs total active habits.

#### Workout instances today

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-vEv0-YZI9h/rows?useColumnNames=true&query=Date:{TODAY}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

#### Interactions logged today

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-bDW7PytKOq/rows?useColumnNames=true&query=Date:{TODAY}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Count interactions and list contacts touched.

#### Social posts today

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows?useColumnNames=true&query=Actual%20post%20date:{TODAY}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Step 3: Get today's Day row

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-Zm8ylxf9zc/rows?useColumnNames=true&query=Date:{TODAY}" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Read the Start of day intent (if set). This frames the debrief.

### Step 4: Compose the debrief

```
## EOD Debrief — {DOW}, {TODAY}

### Today's Intent
"{start_of_day_intent}" (or "No intent set" if blank)

### Tasks
- Completed: {completed_count} personal + {todoist_completed} work
- Carried over: {carryover_count} (still due today, not done)
- New tasks created: {new_count}

### Habits
- {habits_done}/{habits_total} completed
- Streaks maintained: {streaks_list}
- Missed: {missed_habits}

### Workout
- {workout_summary} (or "No workout logged")

### Network
- {interaction_count} interactions logged
- Contacts touched: {contact_names}

### Social
- {posts_count} posts published
- {mentions_triaged} mentions triaged

### Tomorrow Preview
- {tomorrow_meeting_count} meetings
- {tomorrow_tasks_due} tasks due
- Stale contacts to address: {stale_preview}
```

### Step 5: Update the Day row

Write the end-of-day summary back to the Day row:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-Zm8ylxf9zc/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{"cells": [
      {"column": "Date", "value": "{TODAY}"},
      {"column": "End of day summary", "value": "{summary_text}"}
    ]}],
    "keyColumns": ["Date"]
  }'
```

### Step 6: Sync to Supabase history

Upsert today's Day row into `days_history`:

```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/days_history" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation,resolution=merge-duplicates" \
  -d '[{
    "coda_row_id": "{day_row_id}",
    "date": "{TODAY}",
    "start_of_day_intent": "{intent}",
    "end_of_day_summary": "{summary}",
    "sleep": "{sleep}",
    "energy": "{energy}"
  }]'
```

### Step 7: Voice drift check

Load `ross-os-voice-drift` and execute it. This step:
1. Checks if `voice_drift_enabled` is true in Settings
2. Pulls today's X posts via `search_social`
3. Compares against the trained voice profile in Coda (Social Platforms → X)
4. If drift detected, appends a **Voice Drift** section to the debrief

If the drift check is skipped (disabled, insufficient posts, or error), continue without it — never let voice drift block the debrief.

If drift IS detected, add this section to the debrief:

```
### Voice Drift
- Overall: {minor|significant}
- {dimension}: {current} vs baseline {baseline} ({direction})
- Action: Review proposed profile update
```

If drift is `significant`, also send a separate notification with the full drift report so Ross can approve/dismiss changes.

### Step 8: Deliver the debrief

- **If triggered by cron:** Send as notification
- **If triggered manually:** Return as response

### Step 9: Log the run (complete)

PATCH the agent_logs row with status, summary, and detail.

### Step 10: Store memory

```
"Ross OS: Ran eod-debrief at {TODAY} {TIME}. 
{completed_count} tasks done, {habits_done}/{habits_total} habits, 
{interaction_count} interactions, {posts_count} posts."
```

## Error Handling

- If any data source fails, continue with what's available.
- Use `status: partial` if some sections missing.
- A partial debrief is always better than no debrief.
- Coda 429: wait 10s, retry max 3 times.

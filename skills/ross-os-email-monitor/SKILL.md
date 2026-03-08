---
name: ross-os-email-monitor
description: Automated email monitoring agent for Ross OS. Use this skill on an hourly schedule to classify new emails, suggest replies, and create tasks from action items. Runs independently from the Email Daily Brief — this is the real-time classifier, while the brief is the morning summary. Reads Gmail, classifies intent and priority, writes Email-linked Tasks to Coda, and flags items needing attention.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-email-io ross-os-coda-io ross-os-task-creator ross-os-settings-io ross-os-supabase-io ross-os-enhanced-logging
---

# Ross OS — Email Monitor

## When to Use This Skill

Load this skill when:
- The hourly email monitor cron fires
- Ross says "check my email" or "process my inbox"
- You need to classify and triage incoming emails

## Overview

The Email Monitor is the real-time email processing agent. It:
1. Scans for new/unread emails since the last check
2. Classifies each email (intent, priority, sender importance)
3. Creates Email-linked Tasks in Coda for action items
4. Suggests reply drafts for high-priority messages
5. Sends a notification only if there are high-priority items

It does NOT send replies automatically — it surfaces and suggests.

## Credentials & Config

- **Gmail connector:** source_id `gcal`
- **Ross's email:** `ross@trashpanda.capital`
- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Email-linked Tasks Table:** `grid-7IWNsZiHzE`
- **Contacts Table:** `grid-1M2UOaliIC`
- **Settings Table:** `grid-ybi2tIogls`
- **Supabase URL:** `https://fpuhaetqfohxtzhfrmpl.supabase.co`
- **Supabase Key:** `${SUPABASE_SERVICE_ROLE_KEY}`

## Instructions

### Step 0: Pre-flight Checks

1. Load `ross-os-settings-io`. Check `email_monitor_enabled`. If `false`, exit silently.
2. Check `quiet_hours_start` and `quiet_hours_end`. If currently in quiet hours, still process but do NOT send notifications.
3. Log run start to Supabase `agent_logs`:

```bash
SUPABASE_URL="https://fpuhaetqfohxtzhfrmpl.supabase.co"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"

LOG_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"skill_name": "email-monitor", "triggered_by": "schedule", "status": "running"}]')

LOG_ID=$(echo "$LOG_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
```

### Step 1: Fetch New Emails

Search for unread inbox emails from the last 2 hours (overlapping window to avoid missing anything):

```json
{
  "tool_name": "search_email",
  "source_id": "gcal",
  "arguments": {
    "queries": ["is:unread in:inbox"]
  }
}
```

Also fetch recent emails in case some were read but not processed:

```json
{
  "tool_name": "search_email",
  "source_id": "gcal",
  "arguments": {
    "queries": ["in:inbox after:TWO_HOURS_AGO_ISO"]
  }
}
```

Deduplicate by message/thread ID.

### Step 2: Load Contact VIP List

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Build a lookup: `{email_address: {name, importance, company}}`.

### Step 3: Classify Each Email

For each email, determine:

#### Priority (High / Medium / Low)

**High:**
- From a contact with Importance = High
- Contains urgent language: "ASAP", "urgent", "deadline today", "by EOD"
- Direct reply to something Ross sent with a question
- Involves legal/financial terms: "contract", "term sheet", "wire", "sign"
- From a domain associated with active deals

**Medium:**
- From a known contact
- Professional/business context
- Contains a question or request
- Meeting-related

**Low:**
- Newsletters (has unsubscribe link)
- Automated notifications (noreply@, no-reply@)
- Marketing emails
- CC'd but not directly TO ross@trashpanda.capital
- GitHub/Netlify/Stripe/service notifications

#### Intent Classification

| Intent | Description | Action |
|--------|-------------|--------|
| `action_required` | Explicit task or deliverable needed | Create Email-linked Task |
| `reply_needed` | Question asked, awaiting Ross's input | Create task + draft reply |
| `scheduling` | Meeting request, availability | Flag for calendar check |
| `fyi` | Status update, no action needed | Log only |
| `newsletter` | Subscription/marketing | Skip |
| `notification` | Automated service alert | Skip unless error/critical |

### Step 4: Create Tasks for Action Items

For emails classified as `action_required` or `reply_needed`, load `ross-os-task-creator` and create Email-linked Tasks:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Reply to [Sender] re: [Subject summary]"},
        {"column": "Source", "value": "Gmail"},
        {"column": "Due date", "value": "INFERRED_DUE_DATE"},
        {"column": "Notes", "value": "Email summary: [1-2 sentence summary]. Classified as [intent], [priority] priority."},
        {"column": "Context", "value": "Auto-classified by email-monitor"},
        {"column": "Email account", "value": "ross@trashpanda.capital"},
        {"column": "Thread ID link", "value": "GMAIL_THREAD_URL"},
        {"column": "Contact", "value": "SENDER_NAME"}
      ]
    }]
  }'
```

**Due date inference:**
- If email mentions a specific date → use that date
- If "by EOD" / "today" → today
- If "by Friday" / "this week" → that Friday
- If "ASAP" → today
- If no deadline mentioned → tomorrow (default for action items)

### Step 5: Draft Reply Suggestions

For `reply_needed` emails from High or Medium priority senders, draft a suggested reply:

- Keep Ross's voice: direct, professional, not overly formal
- Address the specific question or request
- If scheduling, suggest checking calendar
- Store the draft in the task Notes field: `"Suggested reply: [draft]"`

Do NOT send any replies. Only suggest.

### Step 6: Compose Notification (if needed)

Only notify if there are High-priority items. Respect quiet hours.

```
Title: "[N] emails need attention"
Body:
High Priority:
- [Sender] — [Subject] (Action Required)
  [1-line summary]

- [Sender] — [Subject] (Reply Needed)
  [1-line summary]

[N] tasks created in Email-linked Tasks.
```

If no high-priority items, end silently (no notification).

### Step 7: Log Completion

```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_logs?id=eq.${LOG_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"success\",
    \"completed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"summary\": \"Processed N emails: X high priority, Y tasks created\",
    \"detail\": {
      \"total_processed\": 12,
      \"high_priority\": 2,
      \"medium_priority\": 4,
      \"low_priority\": 6,
      \"tasks_created\": 3,
      \"reply_drafts\": 1,
      \"newsletters_skipped\": 3
    }
  }"
```

### Step 8: Store Memory Entry

```
"Ross OS: Email monitor ran at [time]. Processed [N] emails. 
[X] high priority: [brief list]. [Y] tasks created."
```

## Deduplication Strategy

The monitor runs hourly with a 2-hour lookback window. To avoid creating duplicate tasks:

1. Before creating an Email-linked Task, check if one already exists for the same thread:
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```
2. Search for matching Thread ID link or similar Name
3. If found with Status not Done, skip creation

## Scheduling

The Email Monitor should be scheduled as a Computer cron:

- **Frequency:** Every hour (per Settings: `email_monitor_interval_hours = 1`)
- **Cron expression (UTC):** `0 * * * *` (top of every hour)
- **Background:** `true` (self-contained, no conversation context needed)

To set up:
```
schedule_cron(
  action="create",
  name="Email Monitor",
  cron="0 * * * *",
  task="Load the ross-os-email-monitor skill and execute it.",
  background=true,
  exact=false
)
```

**Important:** Do not schedule until Ross enables `email_monitor_enabled` in Settings.

## Error Handling

- Gmail connector unavailable → Log error, exit gracefully, do not notify
- Coda API rate limited → Wait 10s, retry once, then log partial
- No new emails → Log success with 0 processed, exit silently (no notification)
- Classification uncertain → Default to Medium priority, FYI intent (conservative)
- Contact lookup fails → Still classify but without VIP boosting

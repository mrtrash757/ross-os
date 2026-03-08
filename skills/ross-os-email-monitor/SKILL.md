---
name: ross-os-email-monitor
description: Email intelligence agent for Ross OS. Reads from Coda Gmail Pack sync table (Messages), classifies emails by priority and intent, cross-references Contacts for VIP matching, creates Email-linked Tasks for action items, detects newsletters for unsubscribe candidates, and surfaces stale comms. Runs hourly via cron. Use when the hourly email monitor fires or Ross says "check my email."
metadata:
  author: ross-os
  version: '2.0'
  category: automation
---

# Ross OS — Email Monitor v2

## When to Use This Skill

Load this skill when:
- The hourly email monitor cron fires
- Ross says "check my email" or "process my inbox"
- You need to classify and triage incoming emails

## Overview

The Email Monitor reads from the Coda Gmail Pack sync table (Messages), which syncs all 4 Gmail accounts automatically. It:
1. Reads new/unread emails from the Coda Messages table
2. Cross-references senders against the Contacts table for VIP matching
3. Classifies each email (priority, intent)
4. Creates Email-linked Tasks in Coda for action items
5. Flags unsubscribe candidates
6. Sends a notification only if there are high-priority items

It does NOT send replies automatically — it surfaces and suggests.

## Data Sources

All data lives in Coda doc `nSMMjxb_b2`.

| Table | Grid ID | Purpose |
|-------|---------|---------|
| Messages (Gmail Pack) | grid-sync-1004-Email | Source — synced emails from all 4 accounts |
| Contacts | grid-1M2UOaliIC | VIP matching by sender name/email |
| Email-linked Tasks | grid-7IWNsZiHzE | Destination — tasks created from emails |
| Settings | grid-ybi2tIogls | Config (email_monitor_enabled, quiet hours) |

**Coda API Token:** `f8b53a89-6376-486e-85d8-f59fffed59d1`

**Gmail accounts synced:**
- ross@trashpanda.capital (Workspace — TPC)
- ross@asteriaair.com (Workspace — Asteria Air)
- ross@asteria.partners (Workspace — Asteria Partners)
- ross.kinkade@gmail.com (Personal)

## Instructions

### Step 0: Pre-flight

1. Check Settings table for `email_monitor_enabled`. If `false`, exit silently.
2. Check `quiet_hours_start` and `quiet_hours_end`. If currently in quiet hours (ET), still process but do NOT send notifications.
3. Log run start to Supabase `agent_logs`:

```bash
SUPABASE_URL="https://fpuhaetqfohxtzhfrmpl.supabase.co"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"  # Retrieve from Supabase Vault

LOG_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"skill_name": "email-monitor", "triggered_by": "schedule", "status": "running"}]')

LOG_ID=$(echo "$LOG_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
```

### Step 1: Fetch Unread Emails from Coda

Read the Messages table, filtering for UNREAD emails:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-sync-1004-Email/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1"
```

Filter results in code: only process rows where `Labels` contains `UNREAD`.

Available columns per email row:
- `From` — sender name
- `To` — recipient name
- `Subject` — email subject
- `Date` — ISO timestamp
- `Text` — email body (may be HTML)
- `Labels` — comma-separated Gmail labels (includes Superhuman AI labels)
- `Link` — direct Gmail URL
- `Sync account` — which of the 4 accounts this came from
- `Id` — Gmail message ID
- `Thread` — thread subject
- `Cc`, `Bcc` — if present

### Step 2: Load Contacts for VIP Matching

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1"
```

Build a lookup by name (fuzzy) and org. Contacts have: Name, Org, Role, Importance (High/Med/Low), Context tags, Channels, Cadence.

### Step 3: Classify Each Email

For each unread email, determine:

#### Priority (High / Medium / Low)

**High:**
- From a contact with Importance = High
- Superhuman label `[Superhuman]/AI/Respond` or `[Superhuman]/AI/Waiting`
- Contains urgent language: "ASAP", "urgent", "deadline today", "by EOD"
- Direct reply to something Ross sent (check if thread contains Ross's sent messages)
- Involves legal/financial terms: "contract", "term sheet", "wire", "sign", "invoice"
- From a domain associated with active deals (asteriaair.com, asteria.partners senders)

**Medium:**
- From a known contact (any importance level)
- Superhuman label `[Superhuman]/AI/Meeting`
- Professional/business context
- Contains a question or request
- Meeting-related (calendar invite acceptances, scheduling)

**Low:**
- Superhuman label `[Superhuman]/AI/Marketing` or `[Superhuman]/AI/News`
- Has unsubscribe indicators in body (look for "unsubscribe", "opt out", "email preferences")
- Automated notifications (noreply@, no-reply@, notifications@)
- Label contains `CATEGORY_PROMOTIONS` or `CATEGORY_SOCIAL`
- CC'd but not directly TO one of Ross's accounts
- Service notifications (GitHub, Netlify, Stripe, Supabase, Coda, etc.)

#### Intent Classification

| Intent | Description | Action |
|--------|-------------|--------|
| `action_required` | Explicit task or deliverable needed | Create Email-linked Task |
| `reply_needed` | Question asked, awaiting Ross's input | Create task + note "reply needed" |
| `scheduling` | Meeting request, availability, calendar invite | Flag for calendar check |
| `fyi` | Status update, no action needed | Log only |
| `newsletter` | Subscription/marketing content | Flag as unsubscribe candidate |
| `notification` | Automated service alert | Skip unless error/critical |

### Step 4: Check for Duplicates

Before creating tasks, check existing Email-linked Tasks to avoid duplicates:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1"
```

Skip task creation if a row already exists with the same `Thread ID link` or matching subject/sender.

### Step 5: Create Email-linked Tasks

For emails classified as `action_required` or `reply_needed`:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "[ACTION] Reply to [Sender] re: [Subject summary]"},
        {"column": "Source", "value": "Email Monitor"},
        {"column": "Due date", "value": "INFERRED_DUE_DATE"},
        {"column": "Notes", "value": "From: [sender] via [account]\nPriority: [HIGH/MED]\nIntent: [intent]\n\nSummary: [1-2 sentence summary]\n\nSuggested reply: [draft if reply_needed]"},
        {"column": "Status", "value": "New"},
        {"column": "Context", "value": "Auto-classified by email-monitor v2"},
        {"column": "Email account", "value": "[sync_account]"},
        {"column": "Thread ID link", "value": "[gmail_link]"},
        {"column": "Contact", "value": "[matched_contact_name or sender]"}
      ]
    }]
  }'
```

**Due date inference:**
- Mentions specific date → use that date
- "by EOD" / "today" / "ASAP" → today
- "by Friday" / "this week" → that Friday
- "next week" → next Monday
- No deadline mentioned → tomorrow (default for action items)

**Task name prefixes:**
- `[ACTION]` for action_required
- `[REPLY]` for reply_needed
- `[SCHEDULE]` for scheduling

### Step 6: Build Notification (if needed)

Only notify if there are High-priority items. Respect quiet hours.

Format:
```
Title: "[N] emails need attention"
Body:
📬 Email Monitor — [timestamp]

HIGH PRIORITY:
• [Sender] → [Subject] ([Account])
  [1-line summary] — [Intent]

• [Sender] → [Subject] ([Account])
  [1-line summary] — [Intent]

TASKS CREATED: [N]
NEWSLETTERS FLAGGED: [N]
TOTAL PROCESSED: [N] across [accounts]
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
    \"summary\": \"Processed N emails: X high, Y medium, Z low. T tasks created.\",
    \"detail\": {
      \"total_processed\": 0,
      \"by_account\": {\"trashpanda\": 0, \"asteriaair\": 0, \"partners\": 0, \"personal\": 0},
      \"high_priority\": 0,
      \"medium_priority\": 0,
      \"low_priority\": 0,
      \"tasks_created\": 0,
      \"newsletters_flagged\": 0,
      \"intents\": {\"action_required\": 0, \"reply_needed\": 0, \"scheduling\": 0, \"fyi\": 0, \"newsletter\": 0, \"notification\": 0}
    }
  }"
```

### Step 8: Store Memory Entry

```
"Ross OS: Email monitor ran at [time]. Processed [N] emails across [accounts].
[X] high priority: [brief list]. [Y] tasks created. [Z] newsletters flagged."
```

## Superhuman Label Intelligence

The Gmail Pack brings through Superhuman's AI labels. Leverage these as a first-pass signal:

| Superhuman Label | Meaning | Our Mapping |
|---|---|---|
| `[Superhuman]/AI/Respond` | Needs a reply | → reply_needed, boost to High |
| `[Superhuman]/AI/Waiting` | Waiting for someone else | → fyi (unless overdue) |
| `[Superhuman]/AI/Meeting` | Meeting-related | → scheduling, Medium |
| `[Superhuman]/AI/Marketing` | Marketing/promo | → newsletter, Low |
| `[Superhuman]/AI/News` | News/updates | → fyi, Low |
| `[Superhuman]/ru` | Read/unimportant | → fyi, Low |

These labels augment (not replace) our own classification. If Superhuman says "Respond" but our rules say "Low", boost to Medium minimum.

## Error Handling

- Coda sync table empty → Log warning, exit gracefully, no notification
- Coda API rate limited → Wait 10s, retry once, then log partial
- No unread emails → Log success with 0 processed, exit silently
- Classification uncertain → Default to Medium priority, FYI intent (conservative)
- Contact lookup fails → Still classify without VIP boosting

## Scheduling

Cron: hourly, background=true
```
schedule_cron(
  action="create",
  name="Email Monitor",
  cron="26 * * * *",
  task="Load the ross-os-email-monitor skill and execute it.",
  background=true,
  exact=false
)
```

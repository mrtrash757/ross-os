---
name: ross-os-email-monitor
description: Email intelligence agent for Ross OS. Reads from Coda Gmail Pack sync table (Messages), classifies emails by priority and intent, cross-references Contacts for VIP matching, creates Email-linked Tasks for action items, detects newsletters for unsubscribe candidates, and surfaces stale comms. Runs hourly via cron. Use when the hourly email monitor fires or Ross says "check my email."
metadata:
  author: ross-os
  version: '2.2'
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

### Step 3: Load Settings for Classification

Fetch all rows from the Settings table (`grid-ybi2tIogls`). Build a lookup dict by Key → Value.

The following settings drive classification (all are comma-separated lists):

| Setting Key | Common Name | Purpose |
|------------|-------------|----------|
| `email_high_senders` | Email: High Priority Senders | Always classify as High (e.g. "enilria, mathea head") |
| `email_low_senders` | Email: Low Priority Senders | Always classify as Low/notification (e.g. "noreply, github, google security") |
| `email_newsletter_senders` | Email: Newsletter Senders | Always classify as Low/newsletter (e.g. "controller, history facts") |
| `email_high_domains` | Email: High Priority Domains | Boost emails from these domains |
| `email_urgent_keywords` | Email: Urgent Keywords | Boost to High if found in subject+body |
| `email_legal_finance_keywords` | Email: Legal/Finance Keywords | Boost to High — use PHRASE matching |
| `email_digest_senders` | Email: Digest Senders | Classify as Medium/fyi (e.g. "salesforce, tastytrade") |
| `email_skip_task_intents` | Email: Skip Task Intents | Don't create tasks for these intents (e.g. "fyi, newsletter, notification") |
| `email_max_tasks_per_run` | Email: Max Tasks Per Run | Cap on tasks created per run (default 10) |

**Parse each as a lowercase CSV list:**
```python
def csv_list(key):
    return [x.strip().lower() for x in settings.get(key, "").split(",") if x.strip()]
```

### Step 4: Classify Each Email

For each unread email, apply this classification cascade:

#### 4a. Build matching strings
```python
sender_lower = sender.lower()
text_lower = (subject + " " + body[:500]).lower()
sender_subject_lower = (sender_lower + " " + subject.lower()).strip()
```

#### 4b. Check newsletters and low senders FIRST (before any boosting)
```python
# Newsletter senders → Low/newsletter
is_known_newsletter = any(ns in sender_lower for ns in NEWSLETTER_SENDERS)

# Low senders → Low/notification  
# Match against sender alone, OR sender+subject for multi-word patterns
# e.g. "google security" matches sender "Google" + subject "Security alert"
is_known_low = any(ls in sender_lower for ls in LOW_SENDERS) or \
               any(ls in sender_subject_lower for ls in LOW_SENDERS if len(ls.split()) > 1)

# Superhuman Marketing label (if not also marked Respond)
if is_known_newsletter or (sh_marketing and not sh_respond):
    priority = "Low"; intent = "newsletter"
elif is_known_low:
    priority = "Low"; intent = "notification"
```

#### 4c. High priority signals (only if NOT already classified as newsletter/low)
1. Settings-driven high senders → High
2. VIP contacts (Importance=High in Contacts table) → High  
3. Known contacts (any importance) → Medium minimum
4. Superhuman `Respond` label → High / reply_needed
5. Urgent keywords match → High
6. Legal/finance keyword PHRASE match → High
7. Superhuman `Meeting` label → scheduling intent, Medium minimum
8. Superhuman `News` label → Low (only if no other high signal)
9. `CATEGORY_PROMOTIONS` → Low/newsletter (if not High)

#### 4d. Detect unsubscribe indicators
If body contains "unsubscribe" → flag `is_newsletter = True` (for unsub tracking)

#### 4e. Refine intent for High priority
If classified High but intent is still "fyi":
- Action words ("please", "can you", "need you to") → `action_required`
- Question marks or opinion requests → `reply_needed`
- Otherwise keep as `fyi` (informational high-priority, like Enilria reports)

#### Intent Reference

| Intent | Description | Action |
|--------|-------------|--------|
| `action_required` | Explicit task or deliverable needed | Create Email-linked Task |
| `reply_needed` | Question asked, awaiting Ross's input | Create task + note "reply needed" |
| `scheduling` | Meeting request, availability, calendar invite | Flag for calendar check |
| `fyi` | Status update, no action needed | Log only |
| `newsletter` | Subscription/marketing content | Flag as unsubscribe candidate |
| `notification` | Automated service alert | Skip unless error/critical |

### Step 5: Check for Duplicates

Before creating tasks, check existing Email-linked Tasks to avoid duplicates:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer f8b53a89-6376-486e-85d8-f59fffed59d1"
```

Skip task creation if a row already exists with the same `Thread ID link` or matching subject/sender.

### Step 6: Create Email-linked Tasks

For emails where `needs_task = True` (intent NOT in `email_skip_task_intents` AND no duplicate in existing tasks), create a row in the Email-linked Tasks table.

**Account → Context mapping:**
```python
account_to_context = {
    "ross@asteriaair.com": "Asteria Air",
    "ross@asteria.partners": "Asteria Partners",
    "ross.kinkade@gmail.com": "Personal",
    "ross@trashpanda.capital": "TPC",
}
```

**Task name format:**
- `reply_needed` → "Reply to [Sender] — [Subject]"
- `action_required` → "Action: [Sender] — [Subject]"
- `scheduling` → "Schedule: [Sender] — [Subject]"
- Other → "[Sender]: [Subject]"

**Row payload:**
```json
{
  "rows": [{
    "cells": [
      {"column": "Name", "value": "[prefix] [Sender] — [Subject]"},
      {"column": "Source", "value": "Email from [Sender]"},
      {"column": "Due date", "value": "YYYY-MM-DD"},
      {"column": "Notes", "value": "Priority: [H/M/L] | Intent: [intent]\nAccount: [email]\nReasons: [list]\n\nClassified by RossOS Email Intelligence"},
      {"column": "Status", "value": "Inbox"},
      {"column": "Context", "value": "[mapped context]"},
      {"column": "Email account", "value": "[sync_account]"},
      {"column": "Thread ID link", "value": "[gmail_link]"}
    ]
  }]
}
```

**IMPORTANT: Status must be "Inbox" (not "New").** Context must be one of the valid select options: Personal, Asteria Air, Asteria Partners, Social Intel, TPC, Bot suggestion.

**Due date inference:**
- Mentions specific date → use that date
- "by EOD" / "today" / "ASAP" → today
- "by Friday" / "this week" → that Friday
- "next week" → next Monday
- No deadline mentioned → tomorrow (default for action items)

**Cap:** Do not create more than `email_max_tasks_per_run` tasks per run.

### Step 7: Build Notification (if needed)

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

### Step 8: Log Completion

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

### Step 9: Store Memory Entry

```
"Ross OS: Email monitor ran at [time]. Processed [N] emails across [accounts].
[X] high priority: [brief list]. [Y] tasks created. [Z] newsletters flagged."
```

## Additional Intelligence (included in notification when relevant)

### Response Queue

After classification, build a response queue of emails that need Ross's reply. Include in the notification if any exist.

Criteria (must pass ALL):
1. Not from Ross himself
2. Not a known newsletter, low sender, marketing, or promo email
3. Has at least one signal:
   - Superhuman `Respond` label (urgency = high if still UNREAD)
   - Question mark in subject (only if UNREAD)
   - Action language in body: "can you", "could you", "please", "your thoughts", etc. (only if UNREAD)

Format in notification:
```
RESPONSE NEEDED:
• [Sender] → [Subject] ([Account]) — [signal]
```

### Newsletter Kill List

Track newsletter senders detected during classification. Detection methods:
- Known newsletter sender (from settings)
- Superhuman Marketing label
- CATEGORY_PROMOTIONS Gmail label
- "unsubscribe" / "opt out" in body text
- Superhuman News label

If new newsletter senders are detected that are NOT in `email_newsletter_senders` settings, flag them in the notification so Ross can add them or the agent can auto-add.

### Stale Comms Detection

Cross-reference the Contacts table against email activity:
1. For each contact with a Cadence value, check when the last email was sent/received
2. Also check the Interactions table for last recorded interaction
3. If `days_since_last_contact > cadence_days`, flag as stale
4. If no email or interaction found at all, flag as "never contacted"

Include in notification only if stale High-importance contacts are found.

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

## Superhuman Split Inbox Recommendations

When running a full analysis (not the hourly cron — only when Ross asks to "review inbox" or "optimize inbox"), generate Superhuman split inbox / Gmail filter suggestions:

1. **High-volume sender splits**: Any sender with 3+ emails should get their own split
   - Enilria → "Aviation Intel" split
   - Salesforce Partner Community → "Digests" split
2. **Category-based auto-labels**: CATEGORY_PROMOTIONS → Skip inbox, label Promo
3. **Service notifications**: Reminder, Attio, Supabase, etc. → "Tools/Services" label, skip inbox

These are suggestions only — present to Ross for manual application in Superhuman settings.

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

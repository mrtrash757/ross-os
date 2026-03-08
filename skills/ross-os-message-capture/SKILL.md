---
name: ross-os-message-capture
description: Capture inbound messages from X DMs, LinkedIn DMs, and SMS/iMessage into Ross OS. Use this skill to process messages forwarded via email intake or API, classify them, and create tasks or interactions in Coda. Handles the gap between email (covered by email-monitor) and other messaging channels.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-coda-io ross-os-email-io ross-os-task-creator ross-os-settings-io ross-os-supabase-io
---

# Ross OS — Message Capture

## When to Use This Skill

Load this skill when:
- Ross forwards a message (SMS, DM) to his intake email
- Processing the message intake queue
- Ross asks "check my messages" or "process forwarded messages"
- Building integrations for non-email message channels

## Overview

Not all messages come through email. This skill handles:

| Channel | Capture Method | Status |
|---------|---------------|--------|
| **X DMs** | X API (search_social) or manual forward to intake email | Partial — API read-only |
| **LinkedIn DMs** | Manual forward to intake email (no API for DMs) | Manual intake only |
| **SMS / iMessage** | Manual forward to intake email or Coda form | Manual intake only |
| **Slack** | Slack connector (if connected) | Future |

The core pattern: messages from any channel get normalized into a standard format, classified, and routed to the right Coda table (Interactions, Tasks, or both).

## Credentials & Config

- **Gmail connector:** source_id `gcal`
- **Intake email label:** `Ross-OS-Intake` (Gmail label for forwarded messages)
- **Ross's email:** `ross@trashpanda.capital`
- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Interactions Table:** `grid-bDW7PytKOq`
- **Contacts Table:** `grid-1M2UOaliIC`
- **Email-linked Tasks Table:** `grid-7IWNsZiHzE`
- **Personal Asteria Tasks:** `grid-G1O2W471aC`

## Instructions

### Method 1: Email Intake (Primary)

Ross forwards messages from any channel to his own email with a tag. The message capture skill scans for these.

#### Step 1: Search for Forwarded Messages

```json
{
  "tool_name": "search_email",
  "source_id": "gcal",
  "arguments": {
    "queries": ["label:Ross-OS-Intake is:unread"]
  }
}
```

If no label-based system is set up yet, search for self-forwards:

```json
{
  "tool_name": "search_email",
  "source_id": "gcal",
  "arguments": {
    "queries": ["from:ross@trashpanda.capital to:ross@trashpanda.capital subject:FWD-INTAKE"]
  }
}
```

**Forwarding convention:** Ross forwards messages with subject prefix `FWD-INTAKE: [channel] [contact name]`
- Example: `FWD-INTAKE: X DM @johndoe`
- Example: `FWD-INTAKE: SMS Mom`
- Example: `FWD-INTAKE: LI DM Jane Chen`

#### Step 2: Parse the Forwarded Message

Extract from each intake email:
- **Channel:** X / LinkedIn / SMS / iMessage / WhatsApp / Other
- **Contact:** Who sent the message
- **Content:** The message text
- **Timestamp:** When the original message was sent (if available)
- **Thread context:** Any previous messages in the thread

#### Step 3: Match to Contact

Look up the sender in the Contacts table:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Match by name, X handle, or LinkedIn URL. If no match found, note as "Unknown contact — may need to be added."

#### Step 4: Classify and Route

**Classification:**

| Type | Action |
|------|--------|
| Actionable request | Create task in Personal Asteria Tasks |
| Relationship touch | Log as Interaction |
| Scheduling request | Create task + flag for calendar |
| Casual / social | Log as Interaction only |
| Spam / irrelevant | Skip, no action |

#### Step 5: Log as Interaction

Write to the Interactions table:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-bDW7PytKOq/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Contact", "value": "Jane Chen"},
        {"column": "Date", "value": "2026-03-08"},
        {"column": "Channel", "value": "LinkedIn DM"},
        {"column": "Direction", "value": "Inbound"},
        {"column": "Notes", "value": "Asked about Asteria Air timeline. Wants to schedule a call next week."},
        {"column": "Source", "value": "message-capture"}
      ]
    }]
  }'
```

**Note:** Check the actual Interactions table columns first — the column names above are estimates. Fetch columns with:
```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-bDW7PytKOq/columns" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

#### Step 6: Create Task (if actionable)

If the message requires a response or action, load `ross-os-task-creator`:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Reply to Jane Chen LI DM re: Asteria timeline"},
        {"column": "Due date", "value": "2026-03-09"},
        {"column": "Priority", "value": "Medium"},
        {"column": "Context", "value": "LinkedIn DM forwarded via intake. Jane wants to schedule a call about Asteria Air."},
        {"column": "Source", "value": "message-capture"},
        {"column": "Linked Contact", "value": "Jane Chen"}
      ]
    }]
  }'
```

### Method 2: X DM Check (API-based)

If X API access is available, periodically check for new DMs:

```
search_social(query="to:rossdimaio", only_recent=true)
```

Note: X API access for DMs is limited. This is a best-effort check. The primary capture method remains email forwarding.

### Method 3: Future — Coda Form Intake

A Coda form can be set up as an alternative intake method:
- Ross fills in: Channel, Contact, Message content, Timestamp
- Form writes directly to an intake staging table
- This skill processes the staging table

This is a future enhancement — the email forwarding method works for now.

## Setup Required

### Gmail Label

Create a Gmail label called `Ross-OS-Intake` for forwarded messages. Ross applies this label when forwarding messages from other channels.

Alternatively, use the subject prefix convention (`FWD-INTAKE:`) which requires no Gmail setup.

### Forwarding Shortcuts

Set up quick-forward shortcuts on Ross's phone:
- **iOS Shortcut:** "Forward to Ross OS" — prepends `FWD-INTAKE: [channel]` and sends to ross@trashpanda.capital
- **Manual:** Forward the message with subject `FWD-INTAKE: X DM @handle` (or similar)

## Scheduling

This skill can run:
- **On-demand:** When Ross says "process my messages"
- **As part of Morning Brief:** Add a message intake check step
- **On a schedule:** Every few hours, check for new intake emails

If scheduled:
```
schedule_cron(
  action="create",
  name="Message Capture",
  cron="0 */4 * * *",
  task="Load the ross-os-message-capture skill and execute it. Check for forwarded messages in Gmail intake.",
  background=true,
  exact=false
)
```

## Error Handling

- No intake emails found → Exit silently, log success with 0 processed
- Contact not found → Still process the message, note "Unknown contact" in task/interaction
- Coda API error → Log error, continue with remaining messages
- Ambiguous channel → Default to "Other", let Ross correct manually
- Duplicate detection → Check Interactions table for same contact + same date + similar notes before creating

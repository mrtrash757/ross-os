---
name: ross-os-email-io
description: Search, read, draft, and send emails from Ross's Gmail account. Use this skill when you need to check for new emails, find messages from specific contacts, create email-linked tasks, draft replies, or send messages. Uses the Gmail connector and writes task data to Coda.
metadata:
  author: ross-os
  version: '1.0'
  category: io
---

# Ross OS — Email IO Skill

## When to Use This Skill

Load this skill when you need to:
- Search Ross's inbox for specific emails or senders
- Check for new or unread messages
- Draft or send email replies
- Forward emails
- Create email-linked tasks in Coda from messages
- Scan inbox for action items (used by Morning Brief, Fire Scan)

## Connector: Gmail with Calendar

Source ID: `gcal`

Ross's email: `ross@trashpanda.capital`

### Search Emails

Use `call_external_tool` with:

```json
{
  "tool_name": "search_email",
  "source_id": "gcal",
  "arguments": {
    "queries": ["from:jane@example.com", "subject:contract"]
  }
}
```

**Search syntax (Gmail style):**
- `from:name@email.com` — from a specific sender
- `to:name@email.com` — sent to a specific address
- `subject:keyword` — subject line contains keyword
- `is:unread` — unread messages
- `is:starred` — starred/flagged
- `is:important` — marked important
- `in:inbox` — inbox only
- `label:LabelName` — by label (quote if spaces: `label:"My Label"`)
- `has:attachment` — messages with attachments
- `after:2026-03-01T00:00:00-04:00` — after a date (ISO 8601)
- `before:2026-03-08T00:00:00-04:00` — before a date
- `keyword` — full-text search

**Tips:**
- Use multiple separate queries rather than OR/AND operators
- Keep queries short and specific
- For date searches, include both text-based and date filter queries

### Send an Email

```json
{
  "tool_name": "send_email",
  "source_id": "gcal",
  "arguments": {
    "action": {
      "action": "send",
      "to": ["jane@example.com"],
      "cc": [],
      "bcc": [],
      "subject": "Quick follow-up",
      "body": "Hey Jane,\n\nJust wanted to check in on the Asteria Air timeline.\n\nBest,\nRoss",
      "in_reply_to": null
    },
    "attachment_files": [],
    "user_prompt": null
  }
}
```

- Set `in_reply_to` to an email's `email_id` when replying to thread it correctly.
- Body must be **plain text** (no HTML or Markdown).
- Always use `confirm_action` before sending unless Ross says otherwise.

### Draft an Email (without sending)

```json
{
  "tool_name": "draft_email",
  "source_id": "gcal",
  "arguments": {
    "to": ["jane@example.com"],
    "cc": [],
    "bcc": [],
    "subject": "Re: Asteria Air timeline",
    "body": "Hey Jane,\n\nThanks for the update...",
    "reply_to_email_id": "{original_email_id}",
    "thread_id": "{thread_id}"
  }
}
```

### Forward an Email

```json
{
  "tool_name": "send_email",
  "source_id": "gcal",
  "arguments": {
    "action": {
      "action": "forward",
      "email_id": "{email_id_to_forward}",
      "to": ["teammate@example.com"],
      "cc": [],
      "bcc": []
    },
    "attachment_files": [],
    "user_prompt": null
  }
}
```

## Coda Integration: Email-linked Tasks

When an email requires action, create a task in the Email-linked Tasks table:

**Table:** `grid-7IWNsZiHzE`

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Reply to Jane re: Asteria Air"},
        {"column": "Source", "value": "Gmail"},
        {"column": "Due date", "value": "2026-03-09"},
        {"column": "Status", "value": "New"},
        {"column": "Context", "value": "Asteria Air"},
        {"column": "Email account", "value": "ross@trashpanda.capital"},
        {"column": "Thread ID link", "value": "https://mail.google.com/..."}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

**Email-linked Tasks columns:**
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

## Common Recipes

### Morning inbox scan

```python
# Search for unread emails from the last 24h
search_email(queries=[
    "is:unread",
    "is:important is:unread",
    "after:2026-03-07T00:00:00-04:00 is:unread"
])
```

Then classify each email:
- **Actionable** → Create email-linked task in Coda
- **FYI** → Note in Day summary
- **Spam/noise** → Skip

### Find emails from a contact

```python
search_email(queries=[
    "from:jane@example.com",
    "from:Jane Smith"
])
```

### Check for investor/funding emails

```python
search_email(queries=[
    "from:investor",
    "subject:term sheet",
    "subject:funding",
    "label:Investors"
])
```

## Ross's Email Context

- **Primary:** ross@trashpanda.capital
- **Contexts:** Personal, Asteria Air, Asteria Partners, TPC (Trash Panda Capital)
- **High-priority senders:** Investors, partners, Asteria team, legal
- **Timezone:** US Eastern (EDT UTC-4)

## Error Handling

- **Connector errors:** If `search_email` or `send_email` fails, the gcal connector may need re-auth. Alert Ross.
- **Empty results:** Try broader search terms. Gmail search is strict — shorter queries match more.
- **Coda 429:** Rate limited on task creation. Wait 10 seconds, retry.
- **Always confirm before sending:** Use `confirm_action` with the full draft body.

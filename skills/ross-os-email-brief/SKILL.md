---
name: ross-os-email-brief
description: Generate a daily email summary for Ross's morning briefing. Use this skill to scan the inbox for high-priority emails and required actions, then produce a structured summary that feeds into the Morning Brief. Runs before or as part of the morning brief workflow.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-email-io ross-os-coda-io ross-os-settings-io ross-os-supabase-io
---

# Ross OS — Email Daily Brief

## When to Use This Skill

Load this skill when:
- The Morning Brief needs an email summary section
- Ross asks "what's in my inbox?" or "any important emails?"
- Running as a sub-step of `ross-os-morning-brief`

## Overview

This skill scans Ross's Gmail inbox for emails received since the last brief (or last 24 hours), classifies them by priority and intent, and produces a concise summary. It does NOT replace Superhuman — it surfaces what needs attention.

## Credentials & Config

- **Gmail connector:** source_id `gcal`
- **Ross's email:** `ross@trashpanda.capital`
- **Coda Doc ID:** `nSMMjxb_b2`
- **Contacts Table:** `grid-1M2UOaliIC`

## Instructions

### Step 1: Check Settings

Load `ross-os-settings-io`. Verify `email_monitor_enabled` is `true`. If `false`, skip and return "Email monitoring is disabled in settings."

### Step 2: Fetch Recent Emails

Search for emails from the last 24 hours (or since last brief):

```json
{
  "tool_name": "search_email",
  "source_id": "gcal",
  "arguments": {
    "queries": ["is:inbox after:YESTERDAY_DATE"]
  }
}
```

Replace `YESTERDAY_DATE` with yesterday's date in ISO format (e.g., `2026-03-07T06:30:00-04:00`).

If you need more coverage, also search:

```json
{
  "tool_name": "search_email",
  "source_id": "gcal",
  "arguments": {
    "queries": ["is:unread in:inbox"]
  }
}
```

### Step 3: Classify Each Email

For each email, determine:

1. **Priority** (High / Medium / Low):
   - **High:** From a known high-importance contact, contains action words (deadline, urgent, ASAP, contract, term sheet, funding), is a reply to something Ross sent, involves money
   - **Medium:** From a known contact, professional/business context, requires a response
   - **Low:** Newsletters, notifications, marketing, automated alerts, CC'd only

2. **Intent** (Action Required / FYI / Reply Needed / Scheduling / Newsletter):
   - **Action Required:** Explicit ask, deadline, deliverable needed
   - **Reply Needed:** Question asked, awaiting Ross's input
   - **Scheduling:** Meeting request, availability ask, calendar invite
   - **FYI:** Status update, announcement, no action needed
   - **Newsletter:** Automated digest, marketing, subscription

3. **Contact match:** Check if sender matches a known contact in the Contacts table (`grid-1M2UOaliIC`). If the sender is a high-importance contact, bump priority to High.

### Step 4: Cross-reference with Contacts

Fetch contacts to identify VIPs:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Build a lookup of contact emails and importance levels. Flag any email from a High-importance contact.

### Step 5: Compose the Email Summary

Format the summary as a section that plugs into the Morning Brief:

```
## Inbox Summary

**X new emails since last brief** (Y high priority, Z action required)

### Needs Attention
- **[Sender Name]** — Subject line
  Intent: Action Required | Due: [date if mentioned]
  Summary: One-line summary of what's needed

- **[Sender Name]** — Subject line
  Intent: Reply Needed
  Summary: One-line summary

### FYI / Low Priority
- [Sender] — Subject (Newsletter)
- [Sender] — Subject (FYI)

### Threads Waiting on Others
- Subject — waiting on [person] since [date]
```

### Step 6: Return the Summary

Return the formatted summary text. If called as part of Morning Brief, the parent skill will include it in the notification.

If called standalone, send as a notification:

```
Title: "Inbox Summary — [date]"
Body: [the formatted summary]
```

## Classification Heuristics

### High-Priority Sender Signals
- Email domain matches an active deal (Asteria Air contacts)
- Sender is in Contacts table with Importance = High
- Sender has interacted with Ross in the last 7 days
- Email is a direct reply to something Ross sent

### Action-Required Signals (scan email body)
- Questions directed at Ross ("Can you...", "Could you...", "When will you...")
- Deadline mentions ("by Friday", "EOD", "this week", "ASAP")
- Explicit asks ("Please review", "Need your approval", "Sign and return")
- Calendar/meeting requests
- Document attachments requiring review

### Auto-Low Signals
- Unsubscribe link present → Newsletter
- "noreply@" sender → Automated
- CC'd but not TO'd → FYI
- Known notification senders (GitHub, Netlify, Stripe, etc.)

## Output Format (Structured)

When logging to Supabase, use this detail JSON:

```json
{
  "total_emails": 15,
  "high_priority": 3,
  "action_required": 2,
  "reply_needed": 1,
  "fyi": 8,
  "newsletters": 4,
  "known_contacts": 6,
  "unknown_senders": 9,
  "top_items": [
    {
      "sender": "Jane Chen",
      "subject": "Term sheet review",
      "priority": "high",
      "intent": "action_required"
    }
  ]
}
```

## Error Handling

- If Gmail search returns no results, report "No new emails since last brief"
- If Gmail connector is unavailable, report the error and skip gracefully
- If contacts fetch fails, still classify emails but without VIP boosting
- Always produce a summary even if partial — something is better than nothing

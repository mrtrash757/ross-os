---
name: ross-os-stale-radar
description: Surface overdue contacts and draft outreach suggestions. Use this skill when Ross asks about stale contacts, who he needs to reach out to, overdue touches, or networking follow-ups. Also runs as part of the morning brief for a quick count.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-supabase-io
---

# Ross OS — Stale Contact Radar

## When to Use This Skill

Load this skill when:
- Ross asks "who do I need to reach out to?" or "stale contacts" or "overdue touches"
- Running a deep network health check
- The morning brief flags stale contacts and Ross wants the full list
- Ross wants outreach suggestions or draft messages

## Instructions

### Step 1: Log the run

```bash
SUPABASE_URL="https://fpuhaetqfohxtzhfrmpl.supabase.co"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"

curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"skill_name": "stale-radar", "triggered_by": "manual", "status": "running"}]'
```

### Step 2: Fetch all contacts

Load `ross-os-coda-io`.

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&limit=500" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Step 3: Identify stale contacts

For each contact, check if **Next touch date <= today**. Classify:

**Tiers:**
- **Red (critical):** High importance + overdue by 7+ days
- **Yellow (warning):** High importance + overdue by 1-7 days, OR Med importance + overdue by 14+ days
- **Green (mild):** Med importance + overdue by 1-14 days, OR Low importance + overdue by 30+ days

Sort by: Importance (High first), then days overdue (most overdue first).

### Step 4: Get recent interactions for context

For each stale contact (top 10), check recent interactions:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-bDW7PytKOq/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for interactions matching each contact name. Get the most recent one for context (what was discussed, which channel).

### Step 5: Draft outreach suggestions

For each Red/Yellow contact, suggest an outreach approach:

- **Channel:** Use the contact's preferred channel(s) from the Channels field
- **Tone:** Based on Context tags (Investor → professional, Family → casual, Ally → friendly)
- **Hook:** Reference last interaction topic if available
- **Action type:** Check-in, follow-up, re-engage, or schedule catch-up

Example output per contact:

```
### Jane Smith (Acme Corp, CEO) — RED
**Overdue:** 12 days | **Cadence:** every 14 days | **Last:** Feb 24 via Email
**Last topic:** Discussed Q2 plans
**Suggested outreach:** Quick email check-in on Q2 progress
**Draft:** "Hey Jane, hope Q2 is off to a strong start. Would love to catch up on how things are tracking at Acme. Coffee next week?"
```

### Step 6: Compose the report

```
## Stale Contact Radar — {TODAY}

### Summary
- **Red (critical):** {red_count} contacts
- **Yellow (warning):** {yellow_count} contacts
- Total overdue: {total_stale} contacts

### Red — Needs Immediate Attention
{red_contacts_with_drafts}

### Yellow — Coming Due
{yellow_contacts_with_suggestions}

### Actions
Would you like me to:
1. Create tasks for each outreach?
2. Draft emails for the email-reachable contacts?
3. Queue LinkedIn messages for LI contacts?
```

### Step 7: Offer task creation

If Ross approves, create Personal Asteria Tasks for each outreach:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Reach out to Jane Smith (Acme)"},
        {"column": "Context", "value": "Asteria Partners"},
        {"column": "Source", "value": "Bot suggestion"},
        {"column": "Status", "value": "New"},
        {"column": "Priority", "value": "High"},
        {"column": "Due date", "value": "{tomorrow}"}
      ]
    }]
  }'
```

### Step 8: Log completion

PATCH agent_logs with summary and detail (counts by tier, contacts flagged).

### Step 9: Store memory

```
"Ross OS: Ran stale-radar at {TODAY}. {red_count} red, {yellow_count} yellow, {total_stale} total stale contacts."
```

## Cadence Defaults

If a contact has no Cadence set, use these defaults:
- High importance: 14 days
- Med importance: 30 days
- Low importance: 90 days

## Error Handling

- If Contacts table is empty, report "No contacts found."
- If Interactions table fetch fails, still report stale contacts without context.
- Coda 429: wait 10s, retry.

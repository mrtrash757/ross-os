---
name: ross-os-intel-triage
description: Turn Market Intel Events into actionable Contacts and Tasks with tailored outreach copy. Use this skill to process Status=New intel events, decide which warrant action, create contacts, and draft personalized outreach messages.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-voice-training ross-os-task-creator
---

# Ross OS — Intel Triage

## When to Use This Skill

Load this skill when:
- Ross says "triage my intel" or "process the intel queue"
- New high-priority intel events are flagged by the Morning Brief
- After the LinkedIn Intel Listener or Social Listener writes new events
- Ross wants to act on a specific intel signal

## Overview

Takes raw Market Intel Events and turns them into:
1. New Contacts (if person isn't in the network yet)
2. Tasks with tailored outreach copy (if action is warranted)
3. Updated intel event status (Triaged / Actioned / Ignored)

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Market Intel Events Table:** `grid-HEGLjzzMYd`
- **Contacts Table:** `grid-1M2UOaliIC`
- **Personal Asteria Tasks Table:** `grid-G1O2W471aC`

## Instructions

### Step 1: Load New Intel Events

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Status = New`. Sort by Priority (High first).

### Step 2: Classify Each Event

For each intel event, determine the action:

#### Action: Outreach (create contact + task + draft)
- Person moved into a role where Ross's services/network is relevant
- Company raised funding and may need Ross's expertise
- Known contact changed roles — congratulatory outreach
- Hiring signal at a company Ross wants to connect with

#### Action: Log (update status, no outreach)
- Interesting signal but not immediately actionable
- Company in adjacent space — worth monitoring
- Person at too junior a level for direct outreach

#### Action: Ignore (mark as ignored)
- Signal not relevant after closer inspection
- Duplicate of an already-triaged event
- False positive from the listener

### Step 3: Create Contacts

For Outreach events where the person isn't already a contact:

```bash
# First check if contact exists
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true&query=Name:Jane%20Smith" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

If not found:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Jane Smith"},
        {"column": "Company", "value": "Acme Corp"},
        {"column": "Role", "value": "VP Revenue Operations"},
        {"column": "LinkedIn", "value": "https://linkedin.com/in/janesmith"},
        {"column": "Notes", "value": "Added via intel triage. Job change from OldCo Sr Dir RevOps to VP RevOps at Acme Corp."},
        {"column": "Source", "value": "intel-triage"},
        {"column": "Importance", "value": "Medium"}
      ]
    }]
  }'
```

Update the intel event's `Linked Contact` column.

### Step 4: Draft Outreach

For each Outreach event, draft a personalized message. The outreach should be:

#### Job Change Outreach
- **Tone:** Congratulatory, genuine, not salesy
- **Structure:**
  1. Congrats on the new role
  2. Brief personal connection (how you know them or why you're reaching out)
  3. Light value offer or connection suggestion
  4. Keep it short — 3-4 sentences max

**Example:**
> Congrats on the VP RevOps move at Acme Corp — that's a great fit. I've been following the Salesforce ecosystem closely through my work at Trash Panda Capital and Asteria Air. Would love to connect and hear about what you're building out on the ops side. No agenda, just always interested in what smart RevOps people are doing.

#### Funding Outreach
- **Tone:** Congratulatory, knowledgeable about the space
- **Structure:**
  1. Congrats on the round
  2. Brief context on why it caught your attention
  3. Relevant connection or insight to offer
  4. Open door for conversation

#### Hiring Signal Outreach
- **Tone:** Helpful, networked
- **Structure:**
  1. Noticed they're building out [team]
  2. Offer relevant connections or insights
  3. Keep it helpful, not transactional

### Step 5: Create Tasks with Outreach Drafts

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Outreach: Congrats Jane Smith on VP RevOps at Acme"},
        {"column": "Due date", "value": "2026-03-10"},
        {"column": "Priority", "value": "Medium"},
        {"column": "Context", "value": "Intel: Jane moved from Sr Dir RevOps at OldCo to VP RevOps at Acme Corp. Draft outreach in notes."},
        {"column": "Notes", "value": "DRAFT MESSAGE:\\n\\nCongrats on the VP RevOps move at Acme Corp — that is a great fit..."},
        {"column": "Source", "value": "intel-triage"},
        {"column": "Linked Contact", "value": "Jane Smith"}
      ]
    }]
  }'
```

Update the intel event's `Linked Task` column.

### Step 6: Update Intel Event Status

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "EXISTING_EVENT_NAME"},
        {"column": "Status", "value": "Triaged"},
        {"column": "Notes", "value": "Action: Outreach. Contact created. Task created with draft message."}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

### Step 7: Present Triage Summary

```
## Intel Triage Summary

**Processed:** 6 new events

### Outreach Recommended (2)
1. **Jane Smith** — VP RevOps at Acme Corp (job change)
   Contact created: Yes | Task created: Yes
   Draft: "Congrats on the VP RevOps move at Acme Corp..."
   [Approve outreach / Edit / Skip]

2. **Acme Corp** — Series B ($20M)
   Contact: Already exists | Task created: Yes
   Draft: "Congrats on the round..."
   [Approve outreach / Edit / Skip]

### Logged (3)
- Mike Johnson: Sr Salesforce Admin at TechCo (too junior for direct outreach)
- BigCorp hiring 5 RevOps roles (monitoring)
- StartupX pivot to RevOps tooling (interesting, watching)

### Ignored (1)
- False positive: article mention, not actual job change
```

## Outreach Quality Rules

1. **Never sound automated** — each message must be genuinely personalized
2. **Never be salesy** — Ross builds relationships, not pitches
3. **Reference specifics** — mention their actual company/role, not generic congrats
4. **Keep it short** — 3-5 sentences. Nobody reads long cold messages.
5. **Clear CTA** — "Would love to connect" or "Happy to chat if useful" — something specific but low-pressure
6. **Platform appropriate** — LinkedIn message style differs from X DM or email

## Error Handling

- No new intel events → Report "Intel queue clear"
- Contact creation fails → Log error, still create the task
- Outreach draft seems generic → Flag for manual personalization
- Duplicate contact detected → Skip creation, link existing contact

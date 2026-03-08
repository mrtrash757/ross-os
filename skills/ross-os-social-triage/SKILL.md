---
name: ross-os-social-triage
description: Triage entries in the Social Mentions Inbox. Use this skill to classify mentions as reply/log/ignore, draft responses, and create Contacts or Tasks where appropriate. Processes Status=New mentions and suggests actions for Ross to approve.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-voice-training ross-os-task-creator
---

# Ross OS — Social Triage

## When to Use This Skill

Load this skill when:
- Ross says "triage my mentions" or "check social inbox"
- Processing new Social Mentions Inbox entries
- The Morning Brief flags new high-priority mentions
- After the Social Listener runs and writes new entries

## Overview

For each New mention in the Social Mentions Inbox, this skill:
1. Classifies the appropriate action (Reply / Log / Ignore)
2. Drafts a response using Ross's voice (if Reply)
3. Creates Contacts or Tasks where appropriate
4. Updates the mention's Status

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Social Mentions Inbox:** `grid-LlvuOYy-3t`
- **Contacts Table:** `grid-1M2UOaliIC`
- **Personal Asteria Tasks:** `grid-G1O2W471aC`
- **Social Platforms Table:** `grid-4VBVMRIw_-`

## Instructions

### Step 1: Load New Mentions

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LlvuOYy-3t/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Status = New`. Sort by Priority (High first).

### Step 2: Load Voice Profile

Fetch the voice profile for the mention's platform from Social Platforms table.

### Step 3: Classify Each Mention

#### Reply (engage)
- Direct question to Ross
- Genuine discussion about Ross's expertise area
- From a known/important contact
- From someone with meaningful following in Ross's space
- Positive mention that benefits from acknowledgment
- Constructive criticism worth addressing

#### Log (note but don't engage)
- Brand mention that doesn't need a response
- Repost/share of Ross's content (like/thank internally)
- Industry discussion that mentions Ross tangentially
- Mention from an account with very small reach

#### Ignore (skip)
- Spam or bot accounts
- Trolling or bad-faith engagement
- Automated mentions (bots retweeting)
- Completely irrelevant mentions

### Step 4: Draft Responses (for Reply items)

For each mention classified as Reply:

1. Read the mention content and context
2. Load Ross's voice profile for that platform
3. Draft a response that:
   - Addresses the specific point made
   - Matches Ross's voice and tone
   - Is concise and on-brand
   - Adds value (insight, clarification, appreciation)
   - Doesn't sound like a chatbot or corporate reply

**X reply guidelines:**
- Keep it short — most replies should be 1-2 sentences
- Match the energy of the original post
- Don't over-explain

**LinkedIn reply guidelines:**
- Can be slightly longer
- Professional but warm
- Add genuine value or perspective

### Step 5: Create Contacts (when appropriate)

If a mention comes from someone who should be in Ross's network:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Jane Smith"},
        {"column": "Company", "value": "Acme Corp"},
        {"column": "Notes", "value": "Discovered via X mention about RevOps. Engaged in discussion about Salesforce pricing."},
        {"column": "Source", "value": "social-triage"}
      ]
    }]
  }'
```

Set `Creates Task? = true` on the mention if a follow-up task is warranted.

### Step 6: Create Tasks (when appropriate)

If a mention requires follow-up beyond a quick reply:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Follow up with Jane Smith from X conversation"},
        {"column": "Priority", "value": "Medium"},
        {"column": "Context", "value": "Engaged in X discussion about RevOps. Potential investor or partner."},
        {"column": "Source", "value": "social-triage"},
        {"column": "Linked Contact", "value": "Jane Smith"}
      ]
    }]
  }'
```

Update the mention's `Linked Task` column.

### Step 7: Update Mention Status

After processing, update each mention:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LlvuOYy-3t/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "EXISTING_MENTION_NAME"},
        {"column": "Status", "value": "Triaged"},
        {"column": "Notes", "value": "Action: Reply. Draft: [response text]. Contact created: Yes/No. Task created: Yes/No."}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

### Step 8: Present Triage Summary

```
## Social Triage Summary

**Processed:** 8 new mentions

### Needs Your Reply (3)
1. **@janesmith** (X) — Asked about your RevOps methodology
   Draft reply: "Great question. The biggest shift we made at Asteria was..."
   [Approve / Edit / Skip]

2. **@mike_ops** (X) — Quoted your thread with a follow-up question
   Draft reply: "..."
   [Approve / Edit / Skip]

3. **Sarah Chen** (LinkedIn) — Commented on your fundraising post
   Draft reply: "..."
   [Approve / Edit / Skip]

### Logged (3)
- @techblog reposted your Salesforce take
- @revops_daily mentioned Trash Panda Capital in a roundup
- @founder123 shared your thread

### Ignored (2)
- Bot account retweet
- Spam mention
```

**Important:** Do NOT send replies automatically. Present drafts for Ross to approve, edit, or skip.

## Error Handling

- No new mentions → Report "Inbox clear — no new mentions to triage"
- Voice profile missing → Draft replies using general professional tone, flag for voice training
- Contact creation fails → Log error, continue with remaining mentions
- Ambiguous classification → Default to "Log" (conservative — don't ignore potentially important mentions)

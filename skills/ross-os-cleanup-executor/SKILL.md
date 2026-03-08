---
name: ross-os-cleanup-executor
description: Execute approved cleanup actions from the Network Cleanup Queue. Only acts on Status=Approved entries. Performs disconnect/delete/hide actions via headless browser for LinkedIn, and flags X items for manual Tweet Deleter use. Requires explicit approval for every action.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-coda-io ross-os-headless-sandbox ross-os-settings-io ross-os-supabase-io
---

# Ross OS — Cleanup Executor

## When to Use This Skill

Load this skill when:
- Ross has reviewed and approved items in the Network Cleanup Queue
- Ross says "execute the cleanup" or "run approved cleanups"
- Processing a batch of approved queue entries

## Overview

This is the most sensitive skill in Ross OS. It performs irreversible actions on social platforms. Every action must be:
1. Pre-approved (Status = Approved in the queue)
2. Logged in detail to Supabase
3. Executed one at a time with verification
4. Confirmed after execution

**Key platform rules:**
- **X/Twitter:** Monitor and flag ONLY. Ross uses Tweet Deleter for actual deletion. This skill just marks X items as "Flagged for Tweet Deleter" and updates the queue.
- **LinkedIn:** Headless browser execution for disconnect/delete/hide. Requires Ross's local browser session.
- **Google:** No execution possible. Flag for manual action.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Network Cleanup Queue Table:** `grid-czCy9mvHAb`
- **Supabase URL:** `https://fpuhaetqfohxtzhfrmpl.supabase.co`
- **Supabase Key:** `${SUPABASE_SERVICE_ROLE_KEY}`

## Instructions

### Step 0: Safety Checks

1. Log run start to Supabase `agent_logs` with `skill_name: cleanup-executor`
2. Verify this is not running in quiet hours
3. Count approved items — if more than 20, ask Ross to confirm batch execution

### Step 1: Load Approved Queue Entries

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-czCy9mvHAb/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Status = Approved`. **Never process entries with any other status.**

### Step 2: Group by Platform

Group approved entries by platform for batch processing:
- LinkedIn actions → headless browser via Comet
- X actions → flag for Tweet Deleter (no execution)
- Google actions → manual only (no execution)

### Step 3: Execute LinkedIn Actions

For each approved LinkedIn item, use Ross's local browser:

#### Disconnect a Connection

```python
browser_task(
  url="https://www.linkedin.com/in/{profile_slug}/",
  task="On this LinkedIn profile page, click the 'More' button, then click 'Remove connection' and confirm the removal.",
  use_local_browser={"local": true, "question": "Allow cleanup of LinkedIn connection?"}
)
```

**Wait 5-10 seconds between each disconnection to avoid rate limiting.**

#### Delete a LinkedIn Post

```python
browser_task(
  url="{post_url}",
  task="On this LinkedIn post, click the three-dot menu, select 'Delete', and confirm deletion.",
  use_local_browser={"local": true, "question": "Allow deletion of LinkedIn post?"}
)
```

#### Hide a LinkedIn Post

```python
browser_task(
  url="{post_url}",
  task="On this LinkedIn post, click the three-dot menu, select 'Edit visibility' or 'Hide from profile', and save.",
  use_local_browser={"local": true, "question": "Allow hiding of LinkedIn post?"}
)
```

### Step 4: Handle X Items (Flag Only)

For X/Twitter items, do NOT execute. Instead:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-czCy9mvHAb/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Identifier", "value": "EXISTING_IDENTIFIER"},
        {"column": "Status", "value": "Executed"},
        {"column": "Notes", "value": "Flagged for Tweet Deleter. URL: [tweet_url]. Action: [delete/unlike]. Ross should process in Tweet Deleter app."}
      ]
    }],
    "keyColumns": ["Identifier"]
  }'
```

Tell Ross: "X items have been flagged. Process them in Tweet Deleter: [list of URLs]"

### Step 5: Update Queue Status

After each action:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-czCy9mvHAb/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Identifier", "value": "EXISTING_IDENTIFIER"},
        {"column": "Status", "value": "Executed"},
        {"column": "Notes", "value": "Disconnected on 2026-03-08 at 1:45pm ET. Logged to Supabase."}
      ]
    }],
    "keyColumns": ["Identifier"]
  }'
```

If action failed:
```json
{"column": "Status", "value": "New"},
{"column": "Notes", "value": "Execution failed: [error]. Returned to queue for retry."}
```

### Step 6: Log Every Action

Each individual action gets logged to Supabase `agent_actions`:

```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_actions" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d "[{
    \"log_id\": \"${LOG_ID}\",
    \"action_name\": \"disconnect_linkedin_connection\",
    \"action_type\": \"data_write\",
    \"target_system\": \"linkedin\",
    \"input_summary\": \"Disconnect John Doe (linkedin.com/in/johndoe)\",
    \"status\": \"success\",
    \"completed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }]"
```

### Step 7: Execution Report

```
## Cleanup Execution Report

**Processed:** 15 approved items

### LinkedIn (10)
- Disconnected: 8 connections
- Deleted posts: 1
- Hidden posts: 1
- Failed: 0

### X/Twitter (5)
- Flagged for Tweet Deleter: 5
  - https://x.com/ross/status/123 (delete)
  - https://x.com/ross/status/456 (delete)
  - ...
  Process these in Tweet Deleter when ready.

### Remaining in Queue
- New (awaiting review): 12
- Approved (not yet processed): 0
- Rejected: 3
```

## Safety Guardrails

1. **NEVER process non-Approved items** — this is the most critical rule
2. **NEVER auto-approve** — only Ross can set Status = Approved
3. **One action at a time** with verification — don't batch-execute without checking
4. **Rate limit all platforms** — 5-10 second delays between LinkedIn actions
5. **Log everything** — every action, success or failure, to Supabase
6. **X is monitor-only** — Ross has Tweet Deleter, we just flag
7. **Ask before large batches** — if more than 20 items, get explicit confirmation
8. **Local browser required for LinkedIn** — cannot use cloud browser (no session)

## Error Handling

- Browser action fails → Log error, set Status back to New, continue with next item
- LinkedIn detects automation → Stop immediately, log, notify Ross
- Rate limited → Pause 60 seconds, retry once, then stop batch
- Local browser unavailable → Cannot execute LinkedIn actions, report and exit
- Item already executed (duplicate) → Skip, log warning

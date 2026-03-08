---
name: ross-os-headless-sandbox
description: Secure headless browser environment for network hygiene operations. Use this skill when browsing LinkedIn connections/posts, X posts/likes, or Google search results for cleanup analysis. Provides security patterns, session management, and controlled automation via browser_task.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-coda-io ross-os-settings-io ross-os-supabase-io
---

# Ross OS — Headless Browser Sandbox

## When to Use This Skill

Load this skill when:
- The Cleanup Analyzer needs to browse profiles/posts for analysis
- The Cleanup Executor needs to perform actions (LinkedIn only — X is monitor/flag only)
- Ross says "scan my LinkedIn connections" or "check my old posts"
- Any operation that requires visiting web pages in an automated browser

## Overview

Provides controlled headless browser automation for:
- **LinkedIn:** Browse connections, posts, messages for cleanup analysis. Execute approved deletions.
- **X/Twitter:** Browse posts/likes for analysis only. **Monitor and flag only — do NOT delete** (Ross has Tweet Deleter for that).
- **Google:** Search results analysis for reputation monitoring.

## Security Principles

Per the architecture doc's security guidance:

1. **All actions go through a queue** — never auto-execute destructive actions
2. **Strict logging** — every browser action is logged to Supabase
3. **Minimal cookie lifetime** — don't persist sessions longer than needed
4. **Rate limiting** — respect platform rate limits, add delays between actions
5. **Require manual approval** — destructive actions (delete, disconnect) need Status = Approved in the Cleanup Queue before execution

## How Browser Automation Works

Ross OS uses Perplexity Computer's `browser_task` tool for headless browsing. This runs in an isolated cloud browser — no saved sessions or cookies.

**Important limitation:** The browser environment is isolated. Ross must provide credentials if login is required, or the task must work with public data only.

### Pattern: Browse Public Data

```python
browser_task(
  url="https://x.com/rossdimaio",
  task="Scroll through the last 50 posts. For each post, extract: date, text content, like count, retweet count, reply count. Return as structured data.",
  output_schema={
    "type": "object",
    "properties": {
      "posts": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "date": {"type": "string"},
            "text": {"type": "string"},
            "likes": {"type": "integer"},
            "retweets": {"type": "integer"},
            "replies": {"type": "integer"},
            "url": {"type": "string"}
          }
        }
      }
    }
  }
)
```

### Pattern: Browse LinkedIn (requires login)

LinkedIn browsing requires Ross to be logged in. Options:
1. **Use Comet (local browser):** Ross's local browser has active LinkedIn session. Use `use_local_browser={"local": true}` for browser_task.
2. **Public profiles:** Some data is accessible without login via public profile URLs.
3. **Manual export:** Ross exports data from LinkedIn (connections CSV, etc.) and uploads.

```python
browser_task(
  url="https://www.linkedin.com/mynetwork/invite-connect/connections/",
  task="Scroll through connections list. For each visible connection, extract: name, headline, connection date if shown.",
  use_local_browser={"local": true}
)
```

## Platform-Specific Rules

### X/Twitter — MONITOR AND FLAG ONLY

**Ross has Tweet Deleter. Do not build deletion.**

- Browse posts, likes, reposts
- Analyze content against Network Hygiene Rules
- Flag items for review in Network Cleanup Queue
- **Never delete, unlike, or unrepost** — only write to the queue

### LinkedIn — Browse + Execute (with approval)

- Browse connections, posts, messages
- Analyze against Network Hygiene Rules
- Write suggestions to Network Cleanup Queue
- Execute ONLY items with `Status = Approved`
- Supported actions: Disconnect, Delete post, Hide post

### Google — Search Analysis Only

- Run ego searches for reputation monitoring
- Compare results against desired online presence
- Flag concerning results in the queue
- **No execution** — Google results can't be directly managed

## Logging Requirements

Every browser session must be logged:

```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_actions" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d "[{
    \"log_id\": \"${LOG_ID}\",
    \"action_name\": \"browse_x_posts\",
    \"action_type\": \"api_call\",
    \"target_system\": \"x\",
    \"input_summary\": \"Browsed last 50 posts from @rossdimaio\"
  }]"
```

## Rate Limiting

| Platform | Max requests/session | Delay between | Notes |
|----------|---------------------|---------------|-------|
| X | 50 pages | 3-5s | Respect rate limits |
| LinkedIn | 20 pages | 5-10s | LinkedIn is aggressive about automation |
| Google | 10 searches | 10s | Avoid captchas |

## Error Handling

- Login required → Prompt Ross to use Comet (local browser) or provide session
- Platform blocks automation → Back off, try again later, log the block
- Rate limited → Stop, log progress, resume next run
- Unexpected page structure → Log screenshot path, abort gracefully
- Network error → Retry once, then log and skip

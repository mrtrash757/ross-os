---
name: ross-os-social-io
description: Monitor and manage social media across X (Twitter) and LinkedIn. Use this skill for social listening, mention monitoring, post draft management, network hygiene scanning, and social intel collection. Covers search, content drafting, and the Coda social tables. Does NOT delete tweets (Ross uses Tweet Deleter for that). LinkedIn deletion requires headless browser.
metadata:
  author: ross-os
  version: '1.0'
  category: io
---

# Ross OS — Social IO Skill

## When to Use This Skill

Load this skill when you need to:
- Monitor X (Twitter) for mentions, keywords, or market signals
- Search for social intel (job changes, funding, hiring)
- Draft social posts (X or LinkedIn)
- Manage the Social Mentions Inbox
- Process Network Hygiene Rules and the Cleanup Queue
- Scan for signals defined in Social Listening Rules

## Platform Coverage

| Platform | Read | Write | Delete |
|----------|------|-------|--------|
| X (Twitter) | search_social tool | Manual (not automated) | NO — Ross uses Tweet Deleter app |
| LinkedIn | search_web / browser_task | Manual posting | Browser-based (headless) — queue pattern |

## X (Twitter) — Searching

Use the built-in `search_social` tool:

```python
search_social(
    query="from:rosskinkade",
    num_results=20,
    only_recent=True
)
```

### Search Operators

- `from:username` — Posts from a user (no @)
- `to:username` — Replies to a user
- `@username` — Mentions of a user
- `#hashtag` — Posts with a hashtag
- `keyword` — Full-text search
- `-is:retweet` — Exclude retweets
- `is:reply` / `-is:reply` — Include/exclude replies

### Example Queries

```python
# Ross's recent tweets
search_social(query="from:rosskinkade -is:retweet", num_results=20)

# Mentions of Ross
search_social(query="@rosskinkade", num_results=20)

# Market intel: job changes at specific companies
search_social(query="new role OR just started OR excited to announce Asteria", num_results=30)

# Funding signals
search_social(query="raised funding OR series A OR seed round fintech", num_results=30)

# Competitor monitoring
search_social(query="from:competitorhandle", num_results=20)
```

## LinkedIn — Searching

LinkedIn has no direct API connector. Use these approaches:

1. **Web search** for public profiles and posts:
```python
search_web(queries=["site:linkedin.com/in/ 'Jane Smith' CEO"])
search_vertical(vertical="people", query="Jane Smith CEO Acme Corp")
```

2. **Browser task** for authenticated actions (if Ross is logged in locally):
```python
browser_task(
    url="https://www.linkedin.com/search/results/content/?keywords=asteria",
    task="Search LinkedIn for recent posts mentioning Asteria...",
    use_local_browser={"local": True}
)
```

## Coda Social Tables

### Social Platforms (grid-4VBVMRIw_-)

| Column | Type |
|--------|------|
| Name | text |
| Voice profile | text |
| Target frequency | number (posts/week) |
| Max posts per day | number |

### Social Themes (grid-3IQP9JSQGw)

| Column | Type |
|--------|------|
| Name | text |
| Platform | select |
| Description | text |
| Example post links | link |
| Primary platform | select (X / LI / Both) |

### Social Post Drafts (grid-brOnpRoobl)

| Column | Type |
|--------|------|
| Name | text |
| Platform | lookup |
| Theme | lookup |
| Status | select (Idea / Draft / Ready / Posted / Killed) |
| Core idea | text |
| X draft | text |
| LinkedIn draft | text |
| Target date | date |
| Actual post date | date |
| Link to live post | link |
| Created via | select (Manual / Bot suggestion) |
| Performance | text |

### Social Listening Rules (grid-LNI2nlJZ3X)

| Column | Type |
|--------|------|
| Name | text |
| Platform | select (X / LinkedIn) |
| Query | text |
| Active? | checkbox |
| Frequency | select |
| Category | select (Personal brand / Asteria brand / Market intel) |
| Entity | select (Person / Company / Topic) |
| Signal | select (Mention / Job change / Funding / Hiring / Other) |
| Priority | select (High / Medium / Low) |
| Type | select (Mention / Keyword / Handle / List) |

### Social Mentions Inbox (grid-LlvuOYy-3t)

| Column | Type |
|--------|------|
| Name | text |
| Platform | select |
| Author handle | text |
| Rule | lookup |
| Author type | select (Operator / Investor / Media / Rando / Unknown) |
| Date | date |
| Content | text |
| Link | link |
| Sentiment | select (Positive / Neutral / Negative) |
| Intent | select (Opportunity / Threat / Question / FYI / Spam) |
| Priority | select (High / Medium / Low) |
| Status | select (New / Triaged / Replied / Logged / Ignored) |
| Related Contact | lookup |
| Creates Task? | checkbox |
| Linked Task | lookup |

### Market Intel Events (grid-HEGLjzzMYd)

| Column | Type |
|--------|------|
| Name | text |
| Source platform | select (LinkedIn / X / Other) |
| Rule | lookup |
| Entity type | select (Person / Company) |
| Person name | text |
| Person LI URL | link |
| Old role/company | text |
| New role/company | text |
| Company name | text |
| Signal type | select (Job change / Funding / Hiring / Layoffs / Product launch / Other) |
| Signal date | date |
| Raw text / summary | text |
| Relevance | select (High / Medium / Low) |
| Priority | select (High / Medium / Low) |
| Status | select (New / Triaged / Logged / Actioned / Ignored) |
| Linked Contact | lookup |
| Linked Task | lookup |

### Network Hygiene Rules (grid-OR2yp9QHtp)

| Column | Type |
|--------|------|
| Name | text |
| Rule type | select |
| Trigger | text |
| Frequency | select |
| Platform | select (LinkedIn / X / Patreon / Google / Other) |
| Object type | select (Connection / Post / Message / Search result) |
| Keep criteria | text |
| Purge criteria | text |
| Action type | select (Flag / Delete / Disconnect / Hide) |
| Requires manual confirm? | checkbox |
| Active? | checkbox |

### Network Cleanup Queue (grid-czCy9mvHAb)

| Column | Type |
|--------|------|
| Platform | select |
| Object type | select |
| Identifier | link (URL or ID) |
| Summary | text |
| Reason | text |
| Proposed action | select |
| Status | select (New / Approved / Rejected / Executed) |

## Common Recipes

### Run social listening rules

1. Fetch active rules from Social Listening Rules table
2. For each rule, execute the query on the appropriate platform
3. For each new result, upsert into Social Mentions Inbox or Market Intel Events
4. Set Status = "New" and appropriate Priority

```bash
# Get active listening rules
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LNI2nlJZ3X/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Active? == true`, then run each rule's Query via `search_social`.

### Create a post draft

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Thread on VC portfolio monitoring"},
        {"column": "Status", "value": "Idea"},
        {"column": "Core idea", "value": "How we built a system to track portfolio company signals"},
        {"column": "Created via", "value": "Bot suggestion"},
        {"column": "Target date", "value": "2026-03-10"}
      ]
    }]
  }'
```

### Log a mention to the inbox

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LlvuOYy-3t/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "@investor mentioned Ross"},
        {"column": "Platform", "value": "X"},
        {"column": "Author handle", "value": "@investordude"},
        {"column": "Author type", "value": "Investor"},
        {"column": "Date", "value": "2026-03-08"},
        {"column": "Content", "value": "Great thread by @rosskinkade on..."},
        {"column": "Link", "value": "https://x.com/investordude/status/123"},
        {"column": "Sentiment", "value": "Positive"},
        {"column": "Intent", "value": "FYI"},
        {"column": "Priority", "value": "Medium"},
        {"column": "Status", "value": "New"}
      ]
    }]
  }'
```

### Add to cleanup queue

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-czCy9mvHAb/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Platform", "value": "LinkedIn"},
        {"column": "Object type", "value": "Connection"},
        {"column": "Identifier", "value": "https://linkedin.com/in/spammy-recruiter"},
        {"column": "Summary", "value": "Recruiter, no mutual connections, no interaction in 2+ years"},
        {"column": "Reason", "value": "Matches purge rule: stale recruiter connections"},
        {"column": "Proposed action", "value": "Disconnect"},
        {"column": "Status", "value": "New"}
      ]
    }]
  }'
```

## Deletion Policy

- **X/Twitter:** Ross uses the **Tweet Deleter** app for bulk tweet deletion. This skill only monitors and flags — it does NOT delete tweets.
- **LinkedIn:** Deletion (removing connections, posts, etc.) requires a **headless browser** session via Ross's local browser. Items are queued in the Network Cleanup Queue, then executed via `browser_task` with `use_local_browser`.
- Both platforms use the same queue pattern: flag → review → approve → execute.

## Error Handling

- **search_social rate limits:** Wait between queries if doing bulk listening rule processing.
- **LinkedIn requires login:** Most LinkedIn actions need Ross's local browser session. Alert if unavailable.
- **Coda 429:** Rate limited. Wait 10 seconds, retry. Batch rows when possible.
- **Missing handles:** If a contact's X or LinkedIn handle isn't in the Contacts table, note it and suggest adding.

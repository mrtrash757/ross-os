---
name: ross-os-idea-extraction
description: Mine Ross's notes, Days table entries, intel events, and conversations for social post ideas. Use this skill to scan existing content for post-worthy insights and feed them into the Social Post Drafts table. Turns raw thoughts into structured content seeds.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-settings-io
---

# Ross OS — Idea Extraction

## When to Use This Skill

Load this skill when:
- Ross says "find me post ideas" or "what should I write about?"
- Running a weekly content planning session
- Ross has been logging days/notes and wants to mine them for content
- The social scheduling helper needs ideas to fill the pipeline

## Overview

Ross generates ideas passively through his daily work — Day notes, intel events, meeting takeaways, and task completions. This skill mines those sources and creates structured entries in the Social Post Drafts table.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Days Table:** `grid-Zm8ylxf9zc`
- **Social Post Drafts Table:** `grid-brOnpRoobl`
- **Social Themes Table:** `grid-3IQP9JSQGw`
- **Market Intel Events Table:** `grid-HEGLjzzMYd`
- **Personal Asteria Tasks Table:** `grid-G1O2W471aC`

## Instructions

### Step 1: Define Time Window

Default: last 7 days. Adjust based on how recently this was last run.

### Step 2: Mine Sources

#### Source 1: Days Table (notes, reflections, intent)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-Zm8ylxf9zc/rows?useColumnNames=true&limit=14" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Scan each day's notes for:
- Strong opinions or hot takes
- Lessons learned from specific experiences
- Interesting observations about the market
- Personal stories with a business angle
- Frustrations with tools, processes, or industry norms

#### Source 2: Market Intel Events (industry signals)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows?useColumnNames=true&limit=50" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for recent entries. Look for:
- Funding rounds worth commenting on
- Hiring signals that indicate trends
- Job changes that spark takes
- Product launches relevant to Ross's expertise

#### Source 3: Completed Tasks (accomplishments, insights)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Status = Done` and `Completed at` in the last 7 days. Look for:
- Project milestones worth sharing
- Problems solved that others face
- Tools or workflows built (like Ross OS itself)

#### Source 4: Social Themes (thematic alignment)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-3IQP9JSQGw/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Use existing themes to categorize and prioritize extracted ideas.

### Step 3: Extract and Score Ideas

For each potential idea, assess:

| Criteria | Weight | Description |
|----------|--------|-------------|
| Relevance | High | Does it connect to Ross's expertise / brand? |
| Timeliness | High | Is it happening now? Does timing matter? |
| Uniqueness | Medium | Can Ross add a perspective others can't? |
| Engagement potential | Medium | Will it spark discussion or shares? |
| Platform fit | Medium | Better for X (hot take) or LI (story/insight)? |

Score each idea as Strong / Medium / Weak.

### Step 4: Create Post Draft Entries

For each Strong or Medium idea, create a row in Social Post Drafts:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "Descriptive title of the post idea"},
        {"column": "Core idea", "value": "The core insight or take in 1-2 sentences"},
        {"column": "Platform", "value": "X"},
        {"column": "Theme", "value": "Theme name if matches existing theme"},
        {"column": "Status", "value": "Idea"},
        {"column": "Notes", "value": "Source: Days entry 2026-03-05. Context: Ross noted frustration with Salesforce pricing changes."},
        {"column": "Created via", "value": "idea-extraction"}
      ]
    }]
  }'
```

### Step 5: Deduplicate

Before creating, check existing drafts for similar ideas:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Compare core ideas. Skip if a similar idea already exists with Status not Dropped.

### Step 6: Report Results

Return a summary:
- "Mined [N] sources, found [X] ideas"
- List each idea with title, platform, and score
- Recommend which to develop first based on timeliness

## Idea Templates

Common post patterns that work well for Ross's profile:

| Pattern | X | LinkedIn | Example hook |
|---------|---|----------|-------------|
| Hot take | Yes | No | "Unpopular opinion: [statement]" |
| Lesson learned | Yes | Yes | "Made this mistake so you don't have to:" |
| Industry trend | No | Yes | "Three signals I'm watching in [space]:" |
| Tool/workflow share | Yes | Yes | "Here's how I [solved problem]:" |
| Founder story | No | Yes | "Nobody talks about [aspect of founding]" |
| Quick tip | Yes | No | "[Tool] hack: [tip]" |
| Reaction | Yes | No | "[Person/company] just [did thing]. Here's why it matters:" |

## Error Handling

- If Days table has no notes for the period, report "No day entries to mine" and skip
- If no strong ideas found, report honestly — don't force weak ideas
- If themes table is empty, categorize ideas as "Uncategorized"
- Batch up to 10 draft rows per API call

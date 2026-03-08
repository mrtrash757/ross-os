---
name: ross-os-social-performance
description: Pull engagement metrics from X and LinkedIn, analyze what content performs best, and feed insights back into voice training and idea extraction. Use this skill for weekly performance reviews, content strategy adjustments, and identifying winning patterns.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-social-io ross-os-voice-training
---

# Ross OS — Social Performance Feedback

## When to Use This Skill

Load this skill when:
- Ross asks "how are my posts doing?" or "what's working?"
- Running a weekly content performance review
- Voice training needs data on what resonates
- Adjusting posting strategy based on engagement

## Overview

Closes the feedback loop on social content. Pulls engagement data, updates Social Post Drafts with performance info, identifies patterns, and provides actionable recommendations.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Social Post Drafts Table:** `grid-brOnpRoobl`
- **Social Platforms Table:** `grid-4VBVMRIw_-`
- **Social Themes Table:** `grid-3IQP9JSQGw`

## Instructions

### Step 1: Identify Published Posts to Analyze

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows?useColumnNames=true&limit=200" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Status = Published` and `Performance` column is empty or stale (published more than 24 hours ago without metrics).

### Step 2: Pull Engagement Metrics

#### X Metrics

For each published X post with a live link:

```
search_social(query="from:ROSS_HANDLE", num_results=50)
```

Match posts by content similarity or by the link in `Link to live post`. Extract:
- Likes
- Retweets / Reposts
- Replies
- Quote tweets
- Impressions (if available via API)
- Bookmarks (if available)

#### LinkedIn Metrics

LinkedIn doesn't have a public API for post metrics. Options:
1. **Manual entry:** Ask Ross to update Performance column manually from LinkedIn analytics
2. **Screenshot analysis:** If Ross shares a screenshot of analytics, extract the numbers
3. **Future:** If LinkedIn connector becomes available, automate

### Step 3: Update Performance Data

Write metrics back to Social Post Drafts:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "EXISTING_POST_TITLE"},
        {"column": "Performance", "value": "X: 45 likes, 12 RTs, 8 replies, 3 quotes | Engagement rate: 2.3%"}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

### Step 4: Analyze Patterns

Across all published posts with performance data, identify:

#### What works
- **Top performing posts** (by engagement rate, not just raw numbers)
- **Common patterns** in high performers:
  - Topic/theme
  - Post length
  - Post structure (thread vs. single, story vs. take)
  - Time of day posted
  - Hook type used
  - Tone (more opinionated, more personal, more tactical)

#### What doesn't work
- Lowest performing posts
- Common patterns in underperformers
- Topics to avoid or reframe

#### Trends
- Is engagement trending up or down?
- Which themes are gaining traction?
- Any seasonal or timing patterns?

### Step 5: Generate Performance Report

```
## Social Performance — Week of March 3-8

### X Performance
- Posts published: 4
- Avg likes: 32 | Avg RTs: 8 | Avg replies: 5
- Best performer: "Hot take about Salesforce pricing" (78 likes, 24 RTs)
  - Why it worked: Contrarian opinion, specific numbers, industry pain point
- Worst performer: "Thread on RevOps tools" (8 likes, 1 RT)
  - Why it underperformed: Too generic, no personal angle

### LinkedIn Performance
- Posts published: 2
- Best performer: "Three lessons from building Asteria Air"
  - Strong personal story, relatable founder struggles

### Patterns Identified
- Hot takes outperform educational content 3:1 on X
- Personal stories drive 2x engagement on LinkedIn
- Morning posts (8-10am) outperform evening posts
- Posts under 200 characters perform better on X

### Recommendations
1. Double down on contrarian takes for X
2. Lead with personal stories on LinkedIn
3. Post X content earlier (aim for 8am ET)
4. Current posting cadence is good — maintain 3x/week X, 2x/week LI
```

### Step 6: Feed Insights Back

#### Update Voice Profiles
If patterns show Ross's voice is evolving or certain elements resonate more:
- Note which voice elements drive engagement
- Suggest voice profile updates to `ross-os-voice-training`

#### Inform Idea Extraction
- Which themes/topics should be prioritized?
- What content formats work best?
- Store insights in memory for `ross-os-idea-extraction` to reference

### Step 7: Store in Memory

```
"Ross OS: Social performance week of [date]. X avg engagement: [X]. 
Top performer: [title]. Key insight: [pattern]. LI: [summary]."
```

## Engagement Benchmarks

Starting benchmarks (adjust as data accumulates):

| Metric | X Good | X Great | LI Good | LI Great |
|--------|--------|---------|---------|----------|
| Likes | 20+ | 50+ | 30+ | 100+ |
| Reposts/Shares | 5+ | 15+ | 5+ | 20+ |
| Replies/Comments | 3+ | 10+ | 5+ | 15+ |
| Engagement rate | 1%+ | 3%+ | 2%+ | 5%+ |

These are rough starting points for a growing account. Adjust based on Ross's actual follower count and historical data.

## Scheduling

Run weekly, ideally on Sundays or Mondays:

```
schedule_cron(
  action="create",
  name="Social Performance Review",
  cron="0 14 * * 1",
  task="Load ross-os-social-performance skill and generate a weekly performance report.",
  background=false,
  exact=true
)
```

## Error Handling

- No published posts with links → Report "No posts to analyze — need live post links"
- X API rate limited → Report partial results, try again later
- LinkedIn metrics unavailable → Skip LinkedIn section, note manual entry needed
- Insufficient data (< 5 published posts) → Report "Not enough data for pattern analysis yet"

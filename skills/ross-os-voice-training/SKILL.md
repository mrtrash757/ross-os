---
name: ross-os-voice-training
description: Learn and model Ross's writing voice for X and LinkedIn. Use this skill when building or refining voice profiles, when Ross provides example posts for training, or when other social skills need voice reference for draft generation and editing. Maintains two distinct voice profiles — Ross_X_voice and Ross_LI_voice.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-social-io
---

# Ross OS — Voice Training

## When to Use This Skill

Load this skill when:
- Ross says "train my voice" or "update my voice profile"
- Ross provides example posts for X or LinkedIn
- Building or refining the voice profiles stored in Social Platforms table
- Another skill (draft-generation, editor) needs voice reference
- Ross asks "what does my voice sound like?" or wants to review the profiles

## Overview

Ross writes differently on X vs LinkedIn. This skill:
1. Analyzes Ross's actual posts to extract voice patterns
2. Maintains two voice profiles: `Ross_X_voice` and `Ross_LI_voice`
3. Stores profiles in the Social Platforms table's `Voice profile` column
4. Provides voice reference to draft generation and editing skills

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Social Platforms Table:** `grid-4VBVMRIw_-`
- **Social Post Drafts Table:** `grid-brOnpRoobl`
- **Social Themes Table:** `grid-3IQP9JSQGw`

## Instructions

### Step 1: Gather Training Data

#### From Ross's existing posts (preferred)

Ask Ross for 10-20 example posts per platform, or fetch from X/LI:

**X posts:**
```
search_social(query="from:rossdimaio", num_results=50)
```
(Replace `rossdimaio` with Ross's actual X handle if different.)

**LinkedIn posts:**
LinkedIn requires manual collection. Ask Ross to paste 10-15 of his best LinkedIn posts, or check the Social Post Drafts table for published posts:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows?useColumnNames=true&limit=100" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for: `Status = Published` and `Platform = LinkedIn` or `Platform = X`.

### Step 2: Analyze Voice Patterns

For each platform, analyze the collected posts and extract:

#### Structural Patterns
- **Average length:** character/word count range
- **Sentence structure:** short punchy vs. compound sentences
- **Paragraph pattern:** single-line vs. multi-line, use of line breaks
- **Opening hooks:** how posts start (question, statement, story, stat)
- **Closing pattern:** CTA, question, punchline, no close
- **Thread usage** (X only): frequency, thread structure

#### Tone & Style
- **Formality level:** casual / professional / conversational
- **Humor usage:** frequency, type (dry, self-deprecating, observational)
- **Personal disclosure:** how much personal info is shared
- **Opinion strength:** hedged vs. direct
- **Emoji/punctuation:** usage patterns
- **Hashtag usage:** frequency, style

#### Vocabulary & Phrasing
- **Signature phrases:** words/phrases Ross uses often
- **Industry jargon:** RevOps, SaaS, fundraising terms
- **Contractions:** formal (do not) vs. casual (don't)
- **Sentence starters:** common ways Ross begins sentences
- **Forbidden words:** things Ross would never say

#### Content Patterns
- **Topic distribution:** what Ross writes about
- **Storytelling style:** anecdote-first, insight-first, data-first
- **Engagement style:** asks questions, invites discussion, makes statements
- **Reference style:** links, quotes, screenshots

### Step 3: Build the Voice Profile

Compose a structured voice profile for each platform:

```
## Ross_X_voice

### Identity
- Founder of Trash Panda Capital and Asteria Air
- RevOps/Salesforce ecosystem expert
- Speaks from operator experience, not theory

### Tone
- Direct and confident, not arrogant
- Uses dry humor and occasional self-deprecation
- Conversational — writes like he talks
- Not afraid of strong opinions

### Structure
- Posts are [X-Y] words typically
- Uses line breaks for emphasis
- Opens with [pattern]: hook, question, or bold statement
- Threads for longer takes (3-5 tweets)

### Vocabulary
- Uses: [list of signature words/phrases]
- Avoids: [list of words that don't fit]
- Industry terms: [specific jargon used naturally]

### Rules
- Never sounds like a LinkedIn motivational poster
- No "I'm humbled to announce" energy
- Contractions always (it's, don't, can't)
- Period at end of statements, not exclamation marks
- [Other specific rules]

### Example Posts (Reference)
[3-5 exemplar posts that nail the voice]
```

### Step 4: Store the Voice Profile

Write the voice profile to the Social Platforms table:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-4VBVMRIw_-/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "X"},
        {"column": "Voice profile", "value": "FULL_VOICE_PROFILE_TEXT_HERE"}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

Repeat for LinkedIn. Use `keyColumns: ["Name"]` to upsert (update if platform row exists).

### Step 5: Validate with Ross

Present the voice profiles to Ross for review. Ask:
- "Does this sound like you?"
- "Anything I'm missing or got wrong?"
- "Any phrases you love or hate that I should add?"

Iterate based on feedback and re-save.

## Voice Profile Retrieval (for other skills)

Other skills (draft-generation, editor) retrieve voice profiles with:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-4VBVMRIw_-/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Parse the `Voice profile` column for the target platform.

## Updating Voice Profiles

Voice profiles should be updated when:
- Ross's writing style evolves
- Performance feedback shows certain patterns work better
- Ross provides new example posts or explicit corrections
- After every ~50 published posts, do a refresh analysis

## Error Handling

- If no example posts available, ask Ross to provide some before building the profile
- If Social Platforms table doesn't have X or LinkedIn rows, create them
- If voice profile is empty, other skills should use sensible defaults (direct, professional, concise) and flag that voice training hasn't been run yet

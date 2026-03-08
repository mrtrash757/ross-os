---
name: ross-os-draft-generation
description: Generate X and LinkedIn post drafts from core ideas using Ross's trained voice profiles. Use this skill to turn idea entries in Social Post Drafts into platform-specific drafts. Produces both an X draft and a LinkedIn draft from the same core idea when appropriate.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-voice-training
---

# Ross OS — Draft Generation

## When to Use This Skill

Load this skill when:
- Ross says "draft that post" or "write this up for X/LinkedIn"
- Processing Social Post Drafts entries with Status = Idea
- Ross provides a raw idea and wants platform-ready drafts
- The content pipeline needs drafts generated in batch

## Overview

Takes a core idea and produces platform-specific drafts using the voice profiles from `ross-os-voice-training`. Each idea can produce an X draft, a LinkedIn draft, or both.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Social Post Drafts Table:** `grid-brOnpRoobl`
- **Social Platforms Table:** `grid-4VBVMRIw_-`

## Instructions

### Step 1: Load Voice Profiles

Fetch the voice profiles from Social Platforms:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-4VBVMRIw_-/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Extract `Voice profile` for X and LinkedIn. If voice profiles are empty, use these defaults:
- **X default:** Direct, punchy, conversational. Short sentences. No hashtags. Contractions. Period-ended.
- **LinkedIn default:** Professional but not corporate. Storytelling format. Line breaks for readability. Personal angle on professional topics.

### Step 2: Get Ideas to Draft

#### Single idea (from Ross's request)
Use the idea Ross provides directly.

#### Batch mode (process pipeline)
Fetch undrafted ideas:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows?useColumnNames=true&limit=50" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Status = Idea` and `X draft` is empty and/or `LinkedIn draft` is empty.

### Step 3: Generate Drafts

For each idea, generate platform-specific drafts.

#### X Draft Rules
- **Max length:** 280 characters for single post, or plan a thread (3-5 posts)
- **Voice:** Match Ross_X_voice profile exactly
- **Structure:** Hook in first line. One idea per post. End strong.
- **No hashtags** unless Ross's voice profile says otherwise
- **No emojis** unless Ross's voice profile says otherwise
- **Thread format** (if idea needs more than 280 chars):
  ```
  1/ [Hook — the most provocative part of the take]
  
  2/ [Context or story]
  
  3/ [The insight or lesson]
  
  4/ [Punchline or CTA]
  ```

#### LinkedIn Draft Rules
- **Length:** 200-600 words typical. Can go longer for stories.
- **Voice:** Match Ross_LI_voice profile exactly
- **Structure:**
  - Strong opening line (this is what shows above the fold)
  - Line breaks between every 1-2 sentences
  - Personal angle: "I", "we", stories from experience
  - End with a question or invitation to discuss
- **No "I'm humbled" energy** — ever
- **No generic engagement bait** ("Agree? Like and repost!")

### Step 4: Write Drafts to Coda

Update the existing Social Post Drafts row:

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "EXISTING_TITLE"},
        {"column": "X draft", "value": "THE_X_DRAFT_TEXT"},
        {"column": "LinkedIn draft", "value": "THE_LINKEDIN_DRAFT_TEXT"},
        {"column": "Status", "value": "Draft"}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

Use `keyColumns: ["Name"]` to update the existing row rather than creating a new one.

### Step 5: Present for Review

Show Ross the drafts and ask:
- "Here's the X version and LinkedIn version. Want me to adjust anything?"
- If Ross gives feedback, iterate immediately
- When Ross approves, update Status to "Ready"

## Platform-Specific Guidance

### X Best Practices for Ross
- Lead with the most interesting part — don't bury the lede
- Threads > single tweets for complex ideas (more reach)
- Quote tweets of relevant news with a take > standalone opinions
- Numbers and specifics outperform vague statements
- Contrarian takes get engagement (but only if Ross genuinely believes them)

### LinkedIn Best Practices for Ross
- First line must hook — it's the only thing most people see
- Whitespace is your friend — break up text aggressively
- Personal stories outperform pure analysis
- "Here's what I learned" > "Here's what you should do"
- Tag relevant people/companies when appropriate (but don't tag-spam)
- Post in the morning (8-10am) for best reach

## Dual-Platform Generation

When a core idea works for both platforms:
1. Start with the platform it fits best
2. Adapt — don't just shorten/lengthen
3. X version: tighter, punchier, opinion-forward
4. LinkedIn version: more context, story, professional framing
5. Same core insight, different packaging

When an idea only fits one platform, only generate that draft.

## Error Handling

- Voice profile not found → Use defaults, warn that voice training should be run
- Core idea too vague → Ask Ross to elaborate before drafting
- Draft exceeds platform limits → Restructure as thread (X) or trim (LinkedIn)
- Batch processing → If one idea fails, continue with the rest

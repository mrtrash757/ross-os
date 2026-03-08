---
name: ross-os-social-editor
description: Refine and compress social post drafts without changing Ross's voice or tone. Use this skill to tighten copy, improve hooks, check platform limits, and polish drafts before publishing. Works on both X and LinkedIn content.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-voice-training
---

# Ross OS — Social Editor / Compression

## When to Use This Skill

Load this skill when:
- Ross says "tighten this up" or "edit my draft"
- Ross pastes a draft and asks for feedback
- Processing Social Post Drafts with Status = Draft that need polishing
- A draft exceeds platform character limits

## Overview

This is an editing skill, not a rewriting skill. The goal is to make Ross's drafts better while preserving his voice. Think copy editor, not ghostwriter.

## Credentials & Config

- **Coda Doc ID:** `nSMMjxb_b2`
- **Coda API Token:** `${CODA_API_TOKEN}`
- **Social Post Drafts Table:** `grid-brOnpRoobl`
- **Social Platforms Table:** `grid-4VBVMRIw_-`

## Instructions

### Step 1: Load Voice Profile

Fetch the relevant voice profile from Social Platforms to use as a guardrail:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-4VBVMRIw_-/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Step 2: Get Draft to Edit

Either from Ross directly or from the drafts table:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows?useColumnNames=true&limit=50" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Filter for `Status = Draft`.

### Step 3: Apply Editing Passes

Run these editing passes in order:

#### Pass 1: Hook Check
- Is the first line the strongest part? If not, restructure.
- For X: does the first line make you want to read more?
- For LinkedIn: does it work above the fold?
- Would you stop scrolling for this?

#### Pass 2: Compression
- Remove filler words: "really", "very", "just", "actually", "basically", "honestly"
- Remove hedging: "I think", "kind of", "sort of", "probably" (unless deliberately conversational)
- Remove redundancy: say it once, say it well
- Tighten sentences: fewer words, same meaning
- Example: "I really think that this is basically the wrong approach" → "This is the wrong approach"

#### Pass 3: Voice Alignment
- Compare against the voice profile
- Does it sound like Ross? Would he say this out loud?
- Check for words Ross wouldn't use (per forbidden list in voice profile)
- Make sure contractions match Ross's style
- Check humor/tone alignment

#### Pass 4: Platform Compliance
- **X single post:** Must be under 280 characters
- **X thread:** Each post under 280 chars, thread flows logically
- **LinkedIn:** No hard limit, but 200-600 words is optimal
- Check for platform-inappropriate content (X take on LinkedIn, LinkedIn essay on X)

#### Pass 5: Engagement Optimization
- Does it invite response? (question, provocative statement, relatable frustration)
- Is there a clear takeaway?
- Would someone share/repost this?
- Is the ending strong? (Don't let it fizzle)

### Step 4: Present Edits

Show Ross the original and edited version side by side:

```
**Original:**
[original text]

**Edited:**
[edited text]

**Changes made:**
- Tightened opening hook
- Removed 3 filler words
- Compressed from 310 to 275 characters
- Strengthened closing line
```

Let Ross choose original, edited, or iterate further.

### Step 5: Save Approved Version

```bash
curl -s -X POST "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-brOnpRoobl/rows" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rows": [{
      "cells": [
        {"column": "Name", "value": "EXISTING_TITLE"},
        {"column": "X draft", "value": "EDITED_X_DRAFT"},
        {"column": "LinkedIn draft", "value": "EDITED_LI_DRAFT"},
        {"column": "Status", "value": "Ready"}
      ]
    }],
    "keyColumns": ["Name"]
  }'
```

## Compression Techniques

### For X (when over 280 chars)
1. Replace phrases with shorter equivalents
2. Cut the weakest sentence entirely
3. Use numerals instead of words (3 not three)
4. Remove articles where voice allows (rare for Ross)
5. Split into a thread as last resort

### For LinkedIn (when too long)
1. Cut the weakest paragraph
2. Merge similar points
3. Remove throat-clearing intro paragraphs
4. Trim examples to the strongest one
5. Tighten the ending

## Anti-Patterns (Never Do This)

- Don't add corporate jargon Ross wouldn't use
- Don't add emojis if Ross doesn't use them
- Don't add hashtags unless Ross's style includes them
- Don't soften strong opinions — Ross is direct
- Don't add "What do you think? Comment below!" generic CTAs
- Don't make it longer — editing means shorter
- Don't change the core idea — only refine the expression

## Error Handling

- Draft is empty → Skip, flag for draft generation
- Voice profile missing → Edit using general principles, note that voice training should run
- Draft is already under limits and reads well → Report "Looks good, no edits needed"
- Ross rejects edits → Revert to original, store feedback for future reference

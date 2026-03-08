---
name: ross-os-voice-drift
description: Monitor Ross's X (and eventually LinkedIn) posting style for drift from the trained voice profile. Called as a step in the EOD debrief. Pulls today's posts, compares against stored profile, flags significant changes for review. Use when the EOD debrief runs or when Ross asks to check his voice drift.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-supabase-io
---

# Ross OS — Voice Drift Monitor

## When to Use This Skill

Load this skill when:
- The EOD debrief calls the voice drift check step
- Ross asks "has my voice changed?" or "check my voice drift" or "am I still on brand?"
- You need to compare recent posting behavior against the trained voice profile

## Overview

This skill pulls Ross's recent X posts (since last check), runs them through a structured comparison against the stored voice profile in Coda, and flags any meaningful drift. It does NOT auto-update the profile — it flags changes for Ross's review.

## Credentials

- **Coda**: Doc `nSMMjxb_b2`, API token from `ross-os-coda-io` skill
- **Supabase**: URL and service key from `ross-os-supabase-io` skill
- **X handle**: `@MIAviationKing`
- **Social Platforms table**: `grid-4VBVMRIw_-`
- **Settings table**: `grid-ybi2tIogls`

## Instructions

### Step 1: Check if voice drift monitoring is enabled

Read the Settings table for a row with Key = `voice_drift_enabled`. If the value is `false` or the row doesn't exist, skip silently and return `{ "skipped": true, "reason": "disabled" }`.

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-ybi2tIogls/rows?useColumnNames=true&query=Key:voice_drift_enabled" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

### Step 2: Pull today's posts from X

Use `search_social` to get Ross's posts from today:

```
query: "from:MIAviationKing -is:retweet"
start_time: "{TODAY}T00:00:00Z"  (convert from ET to UTC: subtract 4h for EDT, 5h for EST)
end_time: "{NOW_UTC}"
```

Also pull replies:
```
query: "from:MIAviationKing is:reply"
start_time: same
end_time: same
```

If fewer than 3 total posts+replies today, log "insufficient sample" and return:
```json
{ "skipped": true, "reason": "insufficient_posts", "count": N }
```

Voice drift needs a meaningful sample — don't flag noise from a quiet day.

### Step 3: Load the current voice profile

Fetch the X row from Social Platforms:

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-4VBVMRIw_-/rows?useColumnNames=true&query=Name:X" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Also load the full JSON profile from the repo if available at `voice-profiles/x.json`.

### Step 4: Analyze today's posts against the profile

For each dimension below, compare today's posts to the baseline and score drift as `none`, `minor`, or `significant`:

#### 4a. Length drift
- Calculate avg post length and avg reply length for today
- Compare to baseline: posts 360 chars, replies 149 chars
- **Minor**: >20% deviation from baseline
- **Significant**: >40% deviation from baseline

#### 4b. Profanity drift
- Calculate profanity rate for today's posts
- Compare to baseline: 23%
- **Minor**: >10 percentage point swing
- **Significant**: >20 percentage point swing (e.g., drops to <5% or spikes to >45%)

#### 4c. Topic drift
- Classify each post by content pillar (aviation, tech/AI, entrepreneurship, personal, anti-doomer, calling-out-BS)
- Compare distribution to baseline percentages
- **Minor**: A pillar that normally appears in <10% shows up in >30% of today's posts (or vice versa)
- **Significant**: A dominant pillar (aviation 41%, tech 54%) drops below 10% for the day, OR a new topic not in any pillar appears in >40% of posts

#### 4d. Tone drift
- Check for shifts in tone attributes:
  - Is the confrontational tone absent when it usually appears?
  - Is vulnerability showing up more or less than normal?
  - Are posts unusually short/polished (corporate creep)?
  - Are posts unusually negative without the optimistic pivot?
- **Minor**: 1 tone attribute shifted
- **Significant**: 2+ tone attributes shifted or "corporate creep" detected

#### 4e. Structural drift
- Check multi-paragraph rate, quote tweet rate, media usage rate
- Compare to baselines: 41% multi-para, 31% QTs, 47% media
- **Minor**: One metric >15pp off baseline
- **Significant**: Two+ metrics significantly off

### Step 5: Compose the drift report

If ALL dimensions show `none`: return silently. No notification needed.

If ANY dimension shows `minor` or `significant`, compose a report:

```
## Voice Drift Detected — {TODAY}

**Posts analyzed**: {count} ({originals} posts, {replies} replies)
**Overall drift level**: {minor|significant}

### What shifted:
{For each dimension with drift:}
- **{Dimension}**: {current_value} vs baseline {baseline_value} → {minor|significant}
  - Example: "Post length avg 520 chars vs baseline 360 → significant (+44%)"

### Sample posts showing drift:
{Include 1-2 posts that best illustrate the drift}

### Proposed profile update:
{If significant drift on 2+ dimensions, suggest specific profile changes}
{e.g., "Consider updating avg post length baseline to 400 chars"}
{e.g., "New topic detected: 'policy/regulation' — consider adding as pillar"}

### Action needed:
Ross, review and approve/dismiss these changes. Reply with:
- "approve" to update the voice profile
- "dismiss" to keep current profile (this may be a one-day anomaly)
- Or adjust the proposed changes
```

### Step 6: Deliver the report

- **If called from EOD debrief**: Include the drift summary in the debrief's Social section. If significant, also send a separate notification.
- **If called manually**: Return the full report as response.

### Step 7: Log to Supabase

Log the drift check to `agent_logs`:

```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{
    "skill_name": "voice-drift",
    "triggered_by": "eod-debrief",
    "status": "completed",
    "summary": "{drift_level or skipped reason}",
    "detail": {
      "posts_analyzed": N,
      "dimensions_checked": 5,
      "drift_detected": {"length": "none", "profanity": "minor", ...},
      "overall": "minor"
    }
  }]'
```

### Step 8: If Ross approves changes

When Ross replies "approve" to a drift notification:

1. Read the proposed changes from the notification
2. Load current voice profile JSON from `voice-profiles/x.json`
3. Apply the approved changes (update baselines, add/modify pillars)
4. Write updated profile to Coda Social Platforms table (upsert on Name=X)
5. Commit updated JSON to GitHub at `voice-profiles/x.json`
6. Log the update to Supabase agent_logs
7. Store memory: "Updated X voice profile on {date}: {what changed}"

## Rolling Window (Future Enhancement)

Currently compares against the initial baseline. Future versions should:
- Maintain a 30-day rolling window of daily stats in Supabase
- Use the rolling average as the comparison baseline instead of the initial snapshot
- This prevents the profile from becoming stale while still catching sudden shifts

## Error Handling

- If search_social fails: log error, skip drift check, don't block EOD debrief
- If < 3 posts today: skip silently (insufficient sample)
- If Coda is down: use cached profile from GitHub repo
- Never let a drift check failure block the EOD debrief delivery

## LinkedIn Support (Future)

When LinkedIn voice profile is trained:
1. Add a second platform check in Step 2 (pull LinkedIn posts via Comet browser)
2. Load LinkedIn profile from Social Platforms table (Name=LinkedIn)
3. Run same drift analysis with LinkedIn-specific baselines
4. Combine both platform reports if both have drift

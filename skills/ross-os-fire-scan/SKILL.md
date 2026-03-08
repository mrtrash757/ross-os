---
name: ross-os-fire-scan
description: Quick cross-stack scan for anything urgent or on fire. Use this skill when Ross asks "what's on fire?", "anything urgent?", "what needs my attention right now?", or wants a rapid triage of critical items across all systems.
metadata:
  author: ross-os
  version: '1.0'
  category: workflow
  depends-on: ross-os-coda-io ross-os-todoist-io ross-os-supabase-io
---

# Ross OS — Cross-Stack Fire Scan

## When to Use This Skill

Load this skill when:
- Ross asks "what's on fire?" or "anything urgent?"
- Ross needs a rapid triage across all systems
- Something feels off and Ross wants a quick pulse check
- After being away for a day or more

## Design Philosophy

This is a FAST scan. Not a detailed report — just the fires. Think: smoke alarm, not fire investigation. Get in, check everything, flag what's burning, get out.

## Instructions

### Step 1: Log the run

```bash
SUPABASE_URL="https://fpuhaetqfohxtzhfrmpl.supabase.co"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"

curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"skill_name": "fire-scan", "triggered_by": "manual", "status": "running"}]'
```

### Step 2: Run all checks in parallel

Load `ross-os-coda-io` and `ross-os-todoist-io`. Execute these fetches (batch them to minimize API calls):

#### Check 1: Overdue critical/high tasks

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-G1O2W471aC/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Flag: Status NOT in [Done, Dropped] AND Due date < today AND Priority in [Critical, High]

#### Check 2: Overdue work tasks (Todoist)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid--YZeFkNofZ/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Flag: Due date < today AND Done? != true AND Priority in [p1, p2]

#### Check 3: Email-linked tasks overdue

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-7IWNsZiHzE/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Flag: Status NOT in [Done, Dropped] AND Due date < today

#### Check 4: High-importance stale contacts (critically overdue)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-1M2UOaliIC/rows?useColumnNames=true" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Flag: Importance == "High" AND Next touch date < today - 7 days (a full week overdue)

#### Check 5: High-priority social mentions (untriaged)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-LlvuOYy-3t/rows?useColumnNames=true&query=Status:New" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Flag: Status == "New" AND Priority == "High"

#### Check 6: High-priority intel events (untriaged)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-HEGLjzzMYd/rows?useColumnNames=true&query=Status:New" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Flag: Status == "New" AND Priority == "High"

#### Check 7: Failed agent runs (last 24h)

```bash
curl -s "${SUPABASE_URL}/rest/v1/agent_logs?status=in.(error,partial)&started_at=gte.$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)&order=started_at.desc" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

Flag any failed or partial skill runs.

#### Check 8: Network Cleanup Queue (pending items)

```bash
curl -s "https://coda.io/apis/v1/docs/nSMMjxb_b2/tables/grid-czCy9mvHAb/rows?useColumnNames=true&query=Status:New" \
  -H "Authorization: Bearer ${CODA_API_TOKEN}"
```

Count pending cleanup items (informational, not urgent).

### Step 3: Classify fires

Rate each finding:

- **FIRE** (needs action NOW): Critical/High overdue tasks, high-priority untriaged mentions/intel, failed agent runs
- **SMOKE** (needs attention soon): Medium-priority overdue tasks, stale high-importance contacts, pending cleanup items
- **CLEAR**: Section has no issues

### Step 4: Compose the scan

```
## Fire Scan — {TODAY} {TIME}

### Status: {FIRE_COUNT > 0 ? "🔥 FIRES DETECTED" : "✅ ALL CLEAR"}

{If fires exist:}
### FIRES (act now)
1. **Overdue critical task:** "Review term sheet" — 3 days overdue (Asteria Partners)
2. **High-priority mention:** @investordude asked about partnership — untriaged since Mar 5
3. **Failed agent run:** morning-brief errored at 6:30am — Coda API timeout

{If smoke exists:}
### SMOKE (needs attention)
- 2 medium-priority tasks overdue
- 3 high-importance contacts overdue by 7+ days
- 5 cleanup items pending review

{If all clear:}
### All Clear
No fires or smoke detected. Looking good.

---
{fire_count} fires | {smoke_count} smoke signals | Scanned {check_count} systems
```

### Step 5: Offer actions

If fires are found:
```
Want me to:
1. Create/escalate tasks for the fires?
2. Draft outreach for stale contacts?
3. Triage the high-priority mentions?
4. Investigate the failed agent run?
```

### Step 6: Log completion

PATCH agent_logs. Store memory.

## Performance Target

This scan should complete in under 30 seconds. It's a pulse check, not a deep dive. If Ross wants more detail on any section, they'll ask for the specific skill (stale-radar, etc.).

## Error Handling

- If any single check fails, continue with remaining checks.
- Report which systems couldn't be reached.
- Use `status: partial` if any checks fail.
- Always deliver whatever data was collected.

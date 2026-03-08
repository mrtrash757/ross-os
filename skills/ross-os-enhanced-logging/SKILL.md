---
name: ross-os-enhanced-logging
description: Enhanced real-time agent action logging for Ross OS. Use this skill when any other Ross OS skill runs to log granular actions, state changes, and performance metrics to Supabase beyond the basic start/end pattern. Provides middleware-style logging for audit trail, debugging, and analytics.
metadata:
  author: ross-os
  version: '1.0'
  category: automation
  depends-on: ross-os-supabase-io ross-os-settings-io
---

# Ross OS — Enhanced Logging

## When to Use This Skill

Load this skill when:
- Building or updating any Ross OS workflow skill that needs detailed audit trail
- Debugging a skill execution that failed or produced unexpected results
- Ross asks "what did the agent do?" or "show me the logs"
- You need to log individual actions within a skill run (not just start/end)

## Overview

The basic `agent_logs` table tracks skill-level start/end. This skill adds:
1. **Action-level logging** — each meaningful step within a skill gets a sub-log entry
2. **Structured detail payloads** — standardized JSON in the `detail` column
3. **Performance tracking** — timing data for each action
4. **Error context** — stack traces and retry info on failures

## Supabase Migration Required

Run this migration in the Supabase SQL Editor to add the `agent_actions` table:

```sql
-- Agent Actions table for granular action-level logging
-- Linked to agent_logs for parent skill execution context

CREATE TABLE IF NOT EXISTS agent_actions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  log_id uuid REFERENCES agent_logs(id) ON DELETE CASCADE,
  action_name text NOT NULL,
  action_type text NOT NULL DEFAULT 'api_call',  -- api_call / data_read / data_write / classify / notify / compute
  target_system text,  -- coda / supabase / gmail / gcal / x / linkedin / todoist
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL DEFAULT 'running',  -- running / success / error / skipped
  input_summary text,  -- brief description of what was sent
  output_summary text,  -- brief description of what came back
  row_count integer,  -- number of rows read/written if applicable
  duration_ms integer,  -- computed on completion
  error text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_agent_actions_log ON agent_actions(log_id);
CREATE INDEX idx_agent_actions_type ON agent_actions(action_type);
CREATE INDEX idx_agent_actions_status ON agent_actions(status);

-- RLS: service role only
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on agent_actions"
  ON agent_actions
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
```

## Credentials

- **Supabase URL:** `https://fpuhaetqfohxtzhfrmpl.supabase.co`
- **Service Role Key:** `${SUPABASE_SERVICE_ROLE_KEY}`

## Instructions

### Pattern 1: Wrap a Skill Execution (start + end)

This is the existing pattern from `ross-os-supabase-io`, enhanced with structured detail.

#### Start a skill run

```bash
SUPABASE_URL="https://fpuhaetqfohxtzhfrmpl.supabase.co"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"

LOG_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"skill_name": "SKILL_NAME", "triggered_by": "schedule", "status": "running"}]')

LOG_ID=$(echo "$LOG_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
```

#### Log an individual action within the run

```bash
ACTION_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_actions" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d "[{
    \"log_id\": \"${LOG_ID}\",
    \"action_name\": \"fetch_calendar_events\",
    \"action_type\": \"data_read\",
    \"target_system\": \"gcal\",
    \"input_summary\": \"Today's events 2026-03-08\"
  }]")

ACTION_ID=$(echo "$ACTION_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
```

#### Complete an action (after the actual work)

```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_actions?id=eq.${ACTION_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"success\",
    \"completed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"output_summary\": \"Found 4 events\",
    \"row_count\": 4,
    \"duration_ms\": 1200
  }"
```

#### Complete the skill run

```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_logs?id=eq.${LOG_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"success\",
    \"completed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"summary\": \"Morning brief completed: 4 meetings, 6 tasks, 3 habits\",
    \"detail\": {
      \"meetings\": 4,
      \"tasks_due\": 6,
      \"habits_tracked\": 3,
      \"stale_contacts\": 1,
      \"social_mentions\": 0,
      \"intel_events\": 2
    }
  }"
```

### Pattern 2: Log an Error

```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_actions?id=eq.${ACTION_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"error\",
    \"completed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"error\": \"Gmail API returned 429: rate limit exceeded\",
    \"duration_ms\": 500
  }"
```

Then update the parent log:

```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_logs?id=eq.${LOG_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"partial\",
    \"completed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"summary\": \"Morning brief completed with errors: Gmail unavailable\",
    \"error\": \"Gmail rate limited — email section skipped\"
  }"
```

### Pattern 3: Query Logs for Debugging

#### Recent skill runs
```bash
curl -s "${SUPABASE_URL}/rest/v1/agent_logs?select=*&order=started_at.desc&limit=10" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

#### All actions for a specific run
```bash
curl -s "${SUPABASE_URL}/rest/v1/agent_actions?log_id=eq.${LOG_ID}&order=started_at.asc" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

#### Failed actions in the last 24 hours
```bash
curl -s "${SUPABASE_URL}/rest/v1/agent_actions?status=eq.error&started_at=gte.$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)&order=started_at.desc" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

#### Skill performance (average duration)
```bash
curl -s "${SUPABASE_URL}/rest/v1/rpc/skill_performance" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 7}'
```

(Requires the RPC function below to be created.)

### Optional: Performance Analytics RPC

```sql
CREATE OR REPLACE FUNCTION skill_performance(days_back integer DEFAULT 7)
RETURNS TABLE(
  skill_name text,
  total_runs bigint,
  success_count bigint,
  error_count bigint,
  avg_duration_seconds numeric,
  last_run timestamptz
) AS $$
  SELECT
    l.skill_name,
    count(*) as total_runs,
    count(*) FILTER (WHERE l.status = 'success') as success_count,
    count(*) FILTER (WHERE l.status = 'error') as error_count,
    round(avg(EXTRACT(EPOCH FROM (l.completed_at - l.started_at)))::numeric, 1) as avg_duration_seconds,
    max(l.started_at) as last_run
  FROM agent_logs l
  WHERE l.started_at >= now() - (days_back || ' days')::interval
  GROUP BY l.skill_name
  ORDER BY total_runs DESC;
$$ LANGUAGE sql STABLE;
```

## Standard Action Types

Use these consistently across all skills:

| action_type | When to use |
|-------------|-------------|
| `api_call` | External API call (Coda, Gmail, etc.) |
| `data_read` | Reading data from any source |
| `data_write` | Writing/updating data |
| `classify` | LLM classification or decision |
| `notify` | Sending a notification |
| `compute` | Local computation, filtering, aggregation |

## Standard Target Systems

| target_system | Service |
|---------------|---------|
| `coda` | Coda API |
| `supabase` | Supabase REST API |
| `gmail` | Gmail via connector |
| `gcal` | Google Calendar via connector |
| `x` | X/Twitter API |
| `linkedin` | LinkedIn (headless or API) |
| `todoist` | Todoist (via Coda sync) |
| `attio` | Attio CRM |

## Integration with Existing Skills

When updating existing workflow skills (morning-brief, eod-debrief, etc.) to use enhanced logging:

1. Keep the existing `agent_logs` start/end pattern
2. Add `agent_actions` entries between start and end for each major step
3. Don't over-log — one action per meaningful API call or decision point
4. Typical morning brief has ~8 actions: calendar, tasks, todoist, habits, contacts, social, intel, compose

## Error Handling

- If an action fails, log it as error but continue the parent skill if possible
- Mark parent as `partial` if some actions failed but the skill produced output
- Mark parent as `error` only if the skill could not produce any useful output
- Always include the error message — it's invaluable for debugging

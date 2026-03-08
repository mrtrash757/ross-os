---
name: ross-os-supabase-io
description: Read and write data in the Ross OS Supabase project. Use this skill when you need to log agent runs, query history tables, or store structured data that outlives Coda rows. Covers agent_logs, all 9 history tables, and common query patterns via the REST API.
metadata:
  author: ross-os
  version: '1.0'
  category: io
---

# Ross OS — Supabase IO Skill

## When to Use This Skill

Load this skill when you need to:
- Log the start/end of an agent skill execution (agent_logs)
- Query historical data (days, tasks, habits, workouts, contacts, interactions, social mentions, market intel, cleanup)
- Write synced snapshots from Coda into Supabase history tables
- Build workflow skills that need durable storage or cross-session data

## Credentials

- **Project Ref:** `fpuhaetqfohxtzhfrmpl`
- **Base URL:** stored in env var `SUPABASE_URL`
- **Service Role Key:** stored in env var `SUPABASE_SERVICE_ROLE_KEY`
- **Dashboard:** https://supabase.com/dashboard/project/fpuhaetqfohxtzhfrmpl

Always use the **service role key** for all operations. Every table has RLS enabled with service_role-only policies.

> **Note:** The actual credentials are stored in the Computer skill library version of this skill and in Netlify env vars. This repo copy uses env var references to avoid leaking secrets.

## API Patterns

All calls use `curl` with these headers:

```bash
# Set from environment or Netlify env vars
SUPABASE_URL="${SUPABASE_URL}"
SUPABASE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"
```

### Select rows

```bash
curl -s "${SUPABASE_URL}/rest/v1/{table}?select=*&limit=100" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

Add filters as query params: `?status=eq.running`, `?skill_name=eq.morning-brief`, `?started_at=gte.2026-03-01`.

### Select with ordering

```bash
curl -s "${SUPABASE_URL}/rest/v1/{table}?select=*&order=started_at.desc&limit=10" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

### Insert a row

```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/{table}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{"column": "value", "another": "value"}]'
```

The `Prefer: return=representation` header returns the inserted row (useful for getting the auto-generated `id`).

### Update rows

```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/{table}?id=eq.{uuid}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{"column": "new_value"}'
```

### Upsert rows

```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/{table}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation,resolution=merge-duplicates" \
  -d '[{"coda_row_id": "abc123", "name": "Updated Name"}]'
```

The `resolution=merge-duplicates` header activates upsert on the unique constraint (usually `coda_row_id`).

### Delete rows

```bash
curl -s -X DELETE "${SUPABASE_URL}/rest/v1/{table}?id=eq.{uuid}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

### Count rows

```bash
curl -s -X HEAD "${SUPABASE_URL}/rest/v1/{table}?select=*" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Prefer: count=exact" \
  -I 2>&1 | grep content-range
```

## Table Registry

### agent_logs

Tracks every skill execution. Every workflow skill should log here at start and end.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | uuid | gen_random_uuid() | PK |
| skill_name | text | — | Required. e.g. `morning-brief`, `stale-radar` |
| triggered_by | text | `manual` | `manual` / `schedule` / `skill:{name}` |
| started_at | timestamptz | now() | When the run began |
| completed_at | timestamptz | null | Set on completion |
| status | text | `running` | `running` / `success` / `error` / `partial` |
| summary | text | null | Human-readable result summary |
| detail | jsonb | null | Structured payload (tables touched, row counts, etc.) |
| error | text | null | Error message if status = error |
| created_at | timestamptz | now() | Row creation time |

**Indexes:** `skill_name`, `status`, `started_at DESC`

### History Tables (9 tables)

All history tables follow the same pattern:
- **Unique key:** `coda_row_id` (maps to the Coda row ID for upsert)
- **Sync timestamp:** `synced_at` (auto-set to `now()` on insert)
- **RLS:** service_role only

#### days_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| date | date |
| start_of_day_intent | text |
| end_of_day_summary | text |
| sleep | text |
| energy | text |
| synced_at | timestamptz |

#### tasks_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| task | text |
| context | text |
| source | text |
| status | text |
| priority | text |
| due_date | date |
| assigned_day | date |
| linked_contact | text |
| created_at | timestamptz |
| completed_at | timestamptz |
| synced_at | timestamptz |

#### habits_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| day | date |
| habit_name | text |
| count | integer |
| completed | boolean |
| streak | integer |
| synced_at | timestamptz |

#### workouts_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| day | date |
| workout_name | text |
| planned_start_time | time |
| completed | boolean |
| weight_reps_distance | text |
| duration | text |
| notes | text |
| synced_at | timestamptz |

#### contacts_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| name | text |
| org | text |
| role | text |
| context_tags | text |
| channels | text |
| importance | text |
| cadence | integer |
| last_interaction_date | date |
| next_touch_date | date |
| synced_at | timestamptz |

#### interactions_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| contact_name | text |
| date | date |
| channel | text |
| type | text |
| notes | text |
| related_day | date |
| synced_at | timestamptz |

#### social_mentions_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| platform | text |
| author_handle | text |
| author_type | text |
| date | date |
| content | text |
| link | text |
| sentiment | text |
| intent | text |
| priority | text |
| status | text |
| synced_at | timestamptz |

#### market_intel_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| source_platform | text |
| entity_type | text |
| person_name | text |
| company_name | text |
| signal_type | text |
| signal_date | date |
| raw_text_summary | text |
| relevance | text |
| priority | text |
| status | text |
| synced_at | timestamptz |

#### cleanup_history
| Column | Type |
|--------|------|
| id | bigserial PK |
| coda_row_id | text UNIQUE |
| platform | text |
| object_type | text |
| identifier | text |
| summary | text |
| reason | text |
| proposed_action | text |
| status | text |
| synced_at | timestamptz |

## Common Recipes

### Log a skill run (start)
```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/agent_logs" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '[{
    "skill_name": "morning-brief",
    "triggered_by": "schedule",
    "status": "running"
  }]'
```
Save the returned `id` to update later.

### Log a skill run (complete)
```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_logs?id=eq.{LOG_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "completed_at": "2026-03-08T12:34:00Z",
    "status": "success",
    "summary": "Briefing delivered. 3 tasks due, 1 stale contact.",
    "detail": {"tasks_due": 3, "stale_contacts": 1, "habits_streak": 5}
  }'
```

### Log a skill error
```bash
curl -s -X PATCH "${SUPABASE_URL}/rest/v1/agent_logs?id=eq.{LOG_ID}" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "completed_at": "2026-03-08T12:34:00Z",
    "status": "error",
    "error": "Coda API returned 429 after 3 retries"
  }'
```

### Get recent agent runs
```bash
curl -s "${SUPABASE_URL}/rest/v1/agent_logs?select=*&order=started_at.desc&limit=20" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

### Get failed runs in the last 24h
```bash
curl -s "${SUPABASE_URL}/rest/v1/agent_logs?status=eq.error&started_at=gte.$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)&order=started_at.desc" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

### Sync a Coda row to a history table (upsert)
```bash
curl -s -X POST "${SUPABASE_URL}/rest/v1/tasks_history" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation,resolution=merge-duplicates" \
  -d '[{
    "coda_row_id": "i-abc123def",
    "task": "Follow up with Jane",
    "context": "Asteria Air",
    "source": "Email",
    "status": "In progress",
    "priority": "High",
    "due_date": "2026-03-10"
  }]'
```

### Query history for a date range
```bash
curl -s "${SUPABASE_URL}/rest/v1/days_history?date=gte.2026-03-01&date=lte.2026-03-07&order=date.desc" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

## Logging Protocol

Every workflow skill (Morning Brief, EOD Debrief, Stale Radar, Fire Scan, etc.) MUST:

1. **At start:** Insert an `agent_logs` row with `status: running`. Save the returned `id`.
2. **On success:** PATCH the row with `status: success`, `completed_at`, `summary`, and `detail`.
3. **On error:** PATCH the row with `status: error`, `completed_at`, and `error` message.
4. **On partial:** If some steps succeeded but others failed, use `status: partial` with both `summary` and `error`.

This creates an audit trail visible in the Supabase dashboard and queryable by other skills.

## Filter Operators (PostgREST)

| Operator | Meaning | Example |
|----------|---------|---------|
| eq | equals | `?status=eq.success` |
| neq | not equal | `?status=neq.error` |
| gt | greater than | `?date=gt.2026-03-01` |
| gte | >= | `?started_at=gte.2026-03-01T00:00:00Z` |
| lt | less than | `?date=lt.2026-03-08` |
| lte | <= | `?date=lte.2026-03-07` |
| like | pattern match | `?skill_name=like.*brief*` |
| in | in set | `?status=in.(running,error)` |
| is | null check | `?completed_at=is.null` |

## Error Handling

- **401:** Key invalid or expired. Check `SUPABASE_SERVICE_ROLE_KEY` value.
- **404:** Table not found in schema cache. The table may not exist or PostgREST hasn't reloaded. Wait 30s and retry.
- **409:** Conflict on upsert (duplicate key). Check your unique constraint columns.
- **429:** Rate limited. Wait 10 seconds, retry. Max 3 retries.
- On persistent failure, log the error to `agent_logs` and notify Ross.

# Ross OS — Orchestrator Design

## Core Insight

Perplexity Computer already is the orchestrator. It has skills, subagents, tool access, memory, scheduling, and external connectors. We don't build a separate orchestration engine — we define **skill contracts** that let Computer operate Ross OS as a coherent system.

The "hub-and-spoke" pattern from the architecture doc maps directly to:
- **Hub:** Computer (with memory of Ross OS context, credentials, table IDs)
- **Spokes:** Saved skills that Computer loads on demand

---

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│  Ross (App Layer)                           │
│  Coda doc · Superhuman · Todoist · OneCal   │
├─────────────────────────────────────────────┤
│  Computer (Orchestration Layer)             │
│  Memory · Scheduling · Subagents            │
├─────────────────────────────────────────────┤
│  Skills (Agent Layer)                       │
│  IO Skills    │  Workflows    │  Automations│
│  coda-io      │  morning-brief│  nightly-sync│
│  todoist-io   │  eod-debrief  │  email-monitor│
│  email-io     │  fire-scan    │  social-listen│
│  supabase-io  │  stale-radar  │              │
│  calendar-io  │  intel-triage │              │
│  attio-io     │               │              │
│  social-io    │               │              │
├─────────────────────────────────────────────┤
│  Data Layer                                 │
│  Coda (live state) · Supabase (history)     │
│  External APIs (Gmail, X, LI, Todoist, etc) │
└─────────────────────────────────────────────┘
```

---

## Skill Categories

### 1. IO Skills (read/write data)
Low-level skills that know how to talk to a specific system. Other skills depend on these.

| Skill | System | Capabilities |
|-------|--------|-------------|
| `ross-os-coda-io` | Coda | Read/write any table in Ross OS doc. Table ID registry. Column mappings. |
| `ross-os-todoist-io` | Todoist (via Coda sync) | Read tasks from the Simpladocs sync table. |
| `ross-os-calendar-io` | OneCal / Google Cal | Read today's agenda, upcoming events. |
| `ross-os-email-io` | Gmail / IMAP | Read emails, draft replies. Does not replace Superhuman. |
| `ross-os-supabase-io` | Supabase | Write history records, run analytics queries. |
| `ross-os-attio-io` | Attio | Read investors/deals, append notes. |
| `ross-os-social-io` | X / LI / Patreon | Read feeds, post drafts, headless browser for gaps. |

### 2. Workflow Skills (do a job)
Higher-level skills that compose IO skills to produce an output.

| Skill | Purpose | Uses |
|-------|---------|------|
| `ross-os-morning-brief` | Cross-stack morning summary | coda-io, todoist-io, calendar-io, email-io |
| `ross-os-eod-debrief` | End-of-day summary + logging | coda-io, supabase-io |
| `ross-os-stale-radar` | Surface overdue contacts + draft outreach | coda-io |
| `ross-os-fire-scan` | "What's on fire?" across all systems | coda-io, todoist-io, attio-io |
| `ross-os-intel-triage` | Turn intel events into contacts + tasks | coda-io |
| `ross-os-social-triage` | Triage mentions: reply/log/ignore | coda-io, social-io |

### 3. Automation Skills (run on schedule)
Triggered by Computer's cron scheduler or Netlify scheduled functions.

| Skill | Trigger | Does |
|-------|---------|------|
| Nightly sync | Netlify cron 2am EST | Coda → Supabase ETL (already built) |
| Morning brief | Computer cron 6:30am EST | Runs `ross-os-morning-brief` skill |
| EOD debrief | Computer cron 11pm EST | Runs `ross-os-eod-debrief` skill |
| Email monitor | Computer cron (hourly?) | Classify new emails, create tasks |
| Social listener | Computer cron (every few hours?) | Run listening rules against X/LI |

---

## Skill Contract Format

Every Ross OS skill follows the same pattern:

```yaml
---
name: ross-os-{name}
description: What this skill does and when to load it.
metadata:
  author: ross-os
  version: '1.0'
  category: io | workflow | automation
  depends-on: [list of other ross-os skills it needs]
---
```

### Skill Body Structure

```markdown
# {Skill Name}

## Context
- Ross OS doc ID: nSMMjxb_b2
- Coda API token: stored in Computer memory
- Supabase project: fpuhaetqfohxtzhfrmpl
- (other credentials as needed)

## Table Registry
(for IO skills — maps human names to Coda table/column IDs)

## Instructions
Step-by-step for Computer to execute this skill.

## Outputs
What this skill produces (text summary, Coda rows written, etc.)

## Error Handling
What to do when things fail.
```

---

## Logging Framework

Every skill call gets logged. Two levels:

### 1. Computer Memory (lightweight)
After each skill execution, Computer stores a memory entry:
```
"Ross OS: Ran morning-brief at 2026-03-08 6:30am. 
5 tasks, 3 meetings, 2 stale contacts, 1 social rep."
```
This gives continuity across sessions.

### 2. Supabase (persistent, queryable)
A new `agent_logs` table in Supabase:

| Column | Type | Purpose |
|--------|------|---------|
| id | uuid | PK |
| skill_name | text | Which skill ran |
| triggered_by | text | schedule / manual / another-skill |
| started_at | timestamptz | When it started |
| completed_at | timestamptz | When it finished |
| status | text | success / error / partial |
| summary | text | Human-readable result |
| detail | jsonb | Full structured output |
| error | text | Error message if failed |

This table gets written to via the `ross-os-supabase-io` skill.

---

## How It Works In Practice

### Example: Morning Brief at 6:30am

1. Computer cron fires at 6:30am EST
2. Computer loads `ross-os-morning-brief` skill
3. Morning brief skill instructions say:
   a. Load `ross-os-coda-io` → get today's Day row, tasks, habits, stale contacts, social reps, intel
   b. Load `ross-os-todoist-io` → get work tasks due today
   c. Load `ross-os-calendar-io` → get today's meetings
   d. (Later: Load `ross-os-email-io` → get email summary)
   e. Compose the brief
   f. Send as notification to Ross
   g. Log to Supabase via `ross-os-supabase-io`
4. Computer stores summary in memory for session continuity

### Example: Ross says "What's on fire?"

1. Computer recognizes this maps to `ross-os-fire-scan`
2. Loads the skill
3. Skill pulls overdue/critical items from Coda tasks, Todoist, and Attio
4. Returns prioritized list
5. Ross can then say "create tasks for those" and Computer routes to `ross-os-coda-io`

---

## Build Order for Skills

### Batch 1: Foundation (do first)
1. `ross-os-coda-io` — everything depends on this
2. `ross-os-supabase-io` — logging depends on this
3. `agent_logs` Supabase migration

### Batch 2: Core Workflows
4. `ross-os-todoist-io` — reads from Coda sync table
5. `ross-os-calendar-io` — reads calendar
6. `ross-os-morning-brief` — first real workflow
7. `ross-os-eod-debrief` — second workflow

### Batch 3: Extended IO
8. `ross-os-email-io`
9. `ross-os-attio-io`
10. `ross-os-social-io`

### Batch 4: Advanced Workflows
11. `ross-os-stale-radar`
12. `ross-os-fire-scan`
13. `ross-os-intel-triage`
14. `ross-os-social-triage`

---

## Key Decisions

1. **Computer IS the orchestrator.** No custom routing code. Skills are loaded by name and Computer follows the instructions.

2. **Skills are saved to Computer's skill library.** They persist across sessions. Ross can say "run my morning brief" and Computer knows what to do.

3. **IO skills are shared.** Multiple workflow skills load the same IO skill. `ross-os-coda-io` is the most-loaded skill in the system.

4. **Credentials live in Computer memory + Netlify env vars.** Not hardcoded in skills. Skills reference "the Coda API token from memory" and Computer retrieves it.

5. **Netlify handles time-triggered jobs.** Computer crons handle interactive/notification jobs. Both can invoke the same logic.

6. **Logging is dual-layer.** Memory for continuity, Supabase for analytics and audit trail.

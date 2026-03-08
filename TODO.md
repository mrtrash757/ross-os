# Ross OS — Build Tracker

Master checklist derived from the architecture doc (Section 6: Build Order).
Phases 2 & 3 swapped per Ross's call — infra before agents.

---

## Phase 1 — Coda Base ✅

- [x] Create all 21 tables (20 spec'd + Calendar Mirror bonus)
  - Core Ops: Days, Workouts, Habits, Workout Instances, Habit Logs
  - CRM: Contacts, Interactions, Meetings & Events
  - Tasks: Personal Asteria Tasks, Email-linked Tasks, Todoist Mirror, Calendar Mirror
  - Social Output: Social Platforms, Social Themes, Social Post Drafts
  - Social Listening/Intel: Social Listening Rules, Social Mentions Inbox, Market Intel Events, Hivekiln Import Staging
  - Hygiene: Network Hygiene Rules, Network Cleanup Queue
- [x] Build pages
  - [x] Daily Agenda
  - [x] Contact Directory
  - [x] Social Weekly
  - [x] Intel Log
  - [x] Cleanup Queue
  - [x] Training Dashboard
  - [x] Task Command Center
- [x] Seed sample data (8 tables)
- [ ] Column fixes on 7 tables (Comet task — see `docs/ross-os-fixes.md`)
  - [ ] Days — add missing columns
  - [ ] Contacts — fix column types
  - [ ] Social Platforms — fix column types
  - [ ] Social Listening Rules — fix column types
  - [ ] Network Hygiene Rules — fix column types
  - [ ] Workout Instances — fix column types
  - [ ] Habit Logs — fix column types

---

## Phase 2 — Integrations & Infra 🔧

### Supabase ✅
- [x] Create Supabase project
- [x] Run migration: 9 history tables, 15 indexes, RLS policies
- [x] Verify migration success

### GitHub ✅
- [x] Create repo (`mrtrash757/ross-os`)
- [x] Push initial scaffold (README, migrations, docs, skills)
- [x] Git config + auth working

### Netlify 🔧
- [x] Deploy site — `rossos.netlify.app`
- [x] Connect repo for auto-deploy (main branch)
- [x] Create `netlify.toml` (esbuild bundler, public dir)
- [x] Create `netlify/functions/health.mjs`
- [x] Create `netlify/functions/nightly-sync.mjs` (Coda→Supabase, 9 tables, 2am EST)
- [x] Create `public/index.html` placeholder
- [x] Create `DEPLOYS.md` deploy log
- [x] Create `CHANGELOG.md`
- [x] Create `TODO.md` (this file)
- [ ] Git commit + push new files to trigger auto-deploy
- [ ] Set env vars on Netlify
  - [ ] `CODA_API_TOKEN`
  - [ ] `CODA_DOC_ID`
  - [ ] `SUPABASE_URL`
  - [ ] `SUPABASE_SERVICE_ROLE_KEY`
- [ ] Verify deploy succeeds
- [ ] Test health endpoint (`/.netlify/functions/health`)
- [ ] Test nightly sync (manual trigger or wait for schedule)

### Integrations (not yet started)
- [ ] Wire Todoist → Todoist Mirror table
- [ ] Embed OneCal iframe in Coda

---

## Phase 3 — Agent Architecture ⬜

### Orchestrator
- [ ] Design orchestrator hub-and-spoke pattern
- [ ] Define skill registry / manifest
- [ ] Build logging framework (every skill call logged)

### IO Skills
- [ ] Coda Data Access skill (read/write any table)
- [ ] Todoist Reader skill
- [ ] Calendar Reader skill

### First Agents
- [ ] Morning Brief v1
  - [ ] Pull today's agenda from Days table
  - [ ] Surface high-priority tasks
  - [ ] Social reps for today
  - [ ] Intel block
- [ ] End-of-Day Debrief v1
  - [ ] Summarize completed tasks
  - [ ] Log day summary back to Days table
  - [ ] Flag overdue items

---

## Phase 4 — Automations ⬜

- [ ] Scheduled Morning Brief (daily, 6:30am EST)
- [ ] Scheduled EOD Debrief (daily, 11pm EST)
- [ ] Basic Supabase logging (beyond nightly sync)
- [ ] Task creation automation (agent → Coda/Todoist)
- [ ] Email Daily Brief
  - [ ] Summarize high-priority emails
  - [ ] Surface required actions
- [ ] Message Capture
  - [ ] X/LI DMs via API
  - [ ] SMS/iMessage via manual forwarding (Coda form or special email)

---

## Phase 5 — Fun Stuff ⬜

### Social Output
- [ ] Voice Training — learn `Ross_X_voice` and `Ross_LI_voice`
- [ ] Idea Extraction — mine notes, Days, intel for post ideas
- [ ] Draft Generation — X and LI variants from same core idea
- [ ] Editor / Compression — refine drafts without changing tone
- [ ] Scheduling Helper — apply target frequencies, schedule drafts
- [ ] Performance Feedback — pull engagement metrics, analyze what works

### Social Listening & Intel
- [ ] Social Listener — run rules on X/LI, write to Mentions Inbox + Market Intel
- [ ] Social Triage — suggest reply/log/ignore, draft responses, create Contacts/Tasks
- [ ] LinkedIn Intel Listener — role changes, hiring, funding (Salesforce/RevOps/ICP focus)
- [ ] Intel Triage — turn intel events into Contacts + Tasks with tailored outreach
- [ ] Intel Summary — intel block in Morning Brief, weekly intel recap

### Hygiene & Cleanup
- [ ] Headless browser setup (secure sandbox, strict secrets, logs, minimal cookie lifetime)
  - [ ] LI connections/posts/messages
  - [ ] X posts/likes (monitor/flag only — Ross has Tweet Deleter already)
  - [ ] Patreon posts
  - [ ] Google search results
- [ ] Cleanup Analyzer — apply Network Hygiene Rules to data, write to Cleanup Queue
- [ ] Cleanup Executor — act on Status=Approved entries only
  - Note: Twitter = monitor/flag only (Tweet Deleter handles deletion)
  - Note: LinkedIn = headless browser for deletion
  - Note: Same queue pattern, different execution backends

---

## Notes & Decisions

- **Phase swap:** Original doc has agents (Phase 2) before infra (Phase 3). Ross swapped them — infra first, agents second.
- **Twitter cleanup:** Don't build a deleter. Ross has Tweet Deleter. Only monitor/flag. Same queue pattern, different execution backend.
- **LinkedIn cleanup:** Needs headless browser for deletion actions.
- **Netlify last:** Within Phase 2, Netlify work comes after Supabase and Git.
- **Comet column fixes:** Check in on Comet's progress on the 7 table fixes (see `docs/ross-os-fixes.md`).
- **Coda connector:** Pipedream connector returns null — use direct curl with API token instead.
- **Coda API token:** Scoped to doc `f8b53a89-6376-486e-85d8-f59fffed59d1`, not workspace-wide.

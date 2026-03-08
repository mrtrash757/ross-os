# Ross OS

Personal operating system built on Coda + Supabase + Netlify + Perplexity Computer.

## Architecture

- **Coda** — 21 tables across 5 categories (core ops, CRM, social output, social listening/intel, hygiene/cleanup). The product layer.
- **Supabase** — Postgres warehouse for historical data and analytics. Nightly ETL from Coda.
- **Netlify** — Serverless functions for scheduled jobs (morning brief, EOD debrief, nightly sync).
- **Perplexity Computer** — Agent orchestration layer with specialized IO skills and operator workflows.

## Structure

```
ross-os/
├── supabase/
│   └── migrations/       # SQL migrations for history tables
├── netlify/
│   └── functions/        # Serverless functions (sync, briefs, triggers)
├── skills/               # Agent skill definitions
├── docs/                 # Architecture docs, build guides
└── README.md
```

## Build Order

1. ✅ Phase 1 — Coda Base (21 tables, 7 pages, sample data)
2. 🔧 Phase 2 — Integrations/Infra (Supabase, Netlify, Git)
3. ⬜ Phase 3 — Agent Architecture
4. ⬜ Phase 4 — Automations
5. ⬜ Phase 5 — Fun Stuff

## Coda

- Workspace: Trash Panda Capital (`ws-HBCzjUje1P`)
- Doc: Ross OS (`nSMMjxb_b2`)

## Supabase

- Project: `fpuhaetqfohxtzhfrmpl`
- 9 history tables with indexes and RLS

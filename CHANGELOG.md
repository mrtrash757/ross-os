# Changelog

All notable changes to Ross OS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [0.2.0] — 2026-03-08

### Added
- Netlify serverless functions
  - `nightly-sync.mjs` — Coda→Supabase daily sync (9 tables, 2am EST)
  - `health.mjs` — Health check endpoint
- `netlify.toml` — Build config with esbuild bundler
- `public/index.html` — Landing page
- `package.json` — Project manifest
- `DEPLOYS.md` — Deploy tracking log
- This changelog

## [0.1.0] — 2026-03-07

### Added
- Initial repo scaffold
- Supabase migration (`001_history_tables.sql`)
  - 9 history tables: days, habits, workouts, tasks, contacts, interactions, social_mentions, market_intel, cleanup
  - 15 indexes for query performance
  - Row-level security policies (service role only)
- Architecture documentation (PDF)
- Build guide (PDF)
- Column fixes doc for Coda tables
- Skills directory

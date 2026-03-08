# Ross OS — Deploy Log

Track every deploy with commit hash, what changed, and current status of each component.

---

## Deploy #001 — 2026-03-07

**Commit:** `52d7336`
**Branch:** `main`
**Triggered by:** Initial push
**Status:** ✅ Live

### What shipped
- Repo scaffold (README, .env.example, .gitignore)
- Supabase migration: 9 history tables, 15 indexes, RLS policies
- Architecture docs + build guide + fixes doc
- Skills directory

### Component status
| Component | Status | Notes |
|-----------|--------|-------|
| Coda (21 tables) | ✅ Live | All tables created, sample data seeded |
| Supabase (9 tables) | ✅ Live | Migration ran, RLS enabled |
| Netlify site | ⬜ Placeholder | Repo connected, auto-deploy on |
| Netlify functions | ⬜ Not deployed | Created locally, not pushed yet |
| Agents | ⬜ Not started | Phase 3 |

---

## Deploy #002 — 2026-03-08

**Commit:** _(this push)_
**Branch:** `main`
**Triggered by:** Push to main (auto-deploy)
**Status:** 🚀 Deploying

### What shipped
- `netlify.toml` — build config, function bundler (esbuild)
- `netlify/functions/nightly-sync.mjs` — Coda→Supabase sync, scheduled 2am EST daily
- `netlify/functions/health.mjs` — Health check endpoint (`/.netlify/functions/health`)
- `public/index.html` — Landing page placeholder
- `package.json` — Project manifest
- `DEPLOYS.md` — This deploy log
- `CHANGELOG.md` — Project changelog

### Component status
| Component | Status | Notes |
|-----------|--------|-------|
| Coda (21 tables) | ✅ Live | 7 tables need column fixes (Comet task) |
| Supabase (9 tables) | ✅ Live | Ready for nightly sync |
| Netlify site | ✅ Live | rossos.netlify.app |
| Netlify functions | 🚀 Deploying | nightly-sync + health |
| Env vars | ⬜ Not set | CODA_API_TOKEN, CODA_DOC_ID, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY |
| Agents | ⬜ Not started | Phase 3 |

### Endpoints
- **Site:** https://rossos.netlify.app
- **Health:** https://rossos.netlify.app/.netlify/functions/health
- **Nightly sync:** Scheduled (0 7 * * * UTC)

### Next up
- Set Netlify env vars (4 keys)
- Verify health endpoint returns green
- Column fixes on 7 Coda tables (Comet)
- Phase 3: Agent architecture

---

_Format: Copy the latest block, bump the number, fill in details after each push._

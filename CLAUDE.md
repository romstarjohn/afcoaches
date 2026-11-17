# CLAUDE.md — coachsurmesure

Multi-coach fitness & nutrition platform for people with a West African background. France first, FR (default) + EN.
Offline-first installed PWA (React SPA) + Django/DRF API on the same origin.

Read before working: `docs/definition-of-done.md` (scope, quality bar), `docs/architecture.md` (sync contract),
`docs/backlogs/` (work items).

## Working rules (from the product owner — follow strictly)

1. **Small, testable jobs.** Before implementing a backlog item, split it into steps that each deliver one
   testable behaviour (roughly ≤ 1 hour, a few files). Implement one step, test it, report, then continue.
   If a backlog item is bigger, create follow-up backlog items with the `backlog` skill instead of doing it all at once.
2. **Don't over-build.** Write the code the current step needs, nothing speculative. No long research or
   rewriting of working code unless asked.
3. **Tests: write them, run only what changed.**
   - Every step adds or updates tests for the behaviour it changes.
   - Run only the tests of the area you changed (single file / `-k` / test name). Run the full suite only
     before a commit that touches shared code (settings, auth, sync, API client, shared components).
   - Don't re-run tests for features you didn't touch. Don't re-run a passing suite "just to be sure".
   - Docs/CSS/text-only changes: no test run unless a test asserts that text.
4. **Parallel work:** at most **2** subagents at the same time, only when the tasks are truly independent
   and it saves real time. Prefer cheaper models (`sonnet`, `haiku` for search/mechanical work).
   Default is to do it yourself, sequentially.
5. **Communication:** German by default; concise. Separate facts, assumptions and recommendations.
   Say openly when you disagree. Ask before irreversible or outward-facing actions (push, deploy, deletions).
6. **Git:** commit when a step is done and tested (only when asked or the step is complete). Branch `develop`
   is the default; never force-push. Push only with the user's OK.

## Commands

```bash
# Backend (repo root)
docker compose up -d db                       # Postgres on 127.0.0.1:55432
.venv/bin/python manage.py runserver          # API :8000
.venv/bin/pytest tests/test_api.py -k sync    # targeted tests (preferred)
.venv/bin/ruff check . && .venv/bin/ruff format .

# Frontend (frontend/, Node 22: `nvm use` or ~/.nvm/versions/node/v22.22.2/bin; system node 20.0 is too old)
npm run dev                                   # :5173, proxies /api and /admin to :8000
npx vitest run src/offline/sync.test.ts       # targeted tests (preferred)
npm run lint && npm run typecheck
npm run build                                 # needed to test PWA/service worker (served by Django at :8000)

# Backlog
tools/backlog.py find-duplicates --title "..." --slug "..."
```

## Structure

- `config/` settings/urls · `apps/core` SPA serving, CSP, healthz · `apps/accounts` custom User ·
  `apps/api` auth endpoints · `apps/sync` offline sync registry + push endpoint · `tests/` backend tests
- `frontend/src/` — `api/client.ts` (session + CSRF), `offline/` (Dexie outbox, SyncEngine), `pwa/`,
  `components/`, `pages/`, `locales/fr.json|en.json`
- `docs/` DoD, architecture, backlogs · `tools/backlog.py` · `.claude/skills/` (backlog, pwa-expert, pwa-design)

## Conventions

- No hard-coded UI strings: FR + EN keys in `frontend/src/locales/`; Django gettext for admin/API messages.
- Styles only via tokens in `frontend/src/index.css` (dark blue brand, green actions, app type scale);
  no inline styles (CSP `style-src 'self'`). Use the `pwa-design` / `pwa-expert` skills for UI/PWA work.
- API: DRF, session + CSRF, `IsAuthenticated` by default, every coach endpoint tenant-isolated and tested
  against other coach / follower / anonymous.
- Offline writes go through the outbox + a registered sync handler (client-generated UUIDs, idempotent).
  The service worker never caches `/api/`.
- Followers are read-only (no feedback, no prompts) — enforced server-side.
- No secrets or real personal data in code, fixtures, logs or screenshots.

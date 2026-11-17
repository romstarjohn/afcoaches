# Coach sur mesure

Multi-coach fitness and nutrition platform for people with a West African background (France first, FR/EN).
Installable PWA that keeps working offline and syncs when the connection is back.

- Product scope and quality bar: [`docs/definition-of-done.md`](docs/definition-of-done.md)
- Architecture and sync contract: [`docs/architecture.md`](docs/architecture.md)
- Backlog: [`docs/backlogs/`](docs/backlogs/) — managed with `tools/backlog.py` (see `.claude/skills/backlog/SKILL.md`)

## Stack

- **Backend:** Django 5.2 LTS · Django REST Framework · PostgreSQL 17 · WhiteNoise · Gunicorn
- **Frontend (`frontend/`):** React 19 · TypeScript · Vite · vite-plugin-pwa (Workbox) · Dexie (IndexedDB) ·
  i18next (FR default, EN) · Vitest
- One Docker image serves API, admin and the built PWA from the same origin.

## Local setup

Requirements: Python 3.13, Node 22 (`nvm use`), Docker, gettext (`brew install gettext` on macOS).

```bash
# Backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env                 # local values only, never commit .env
docker compose up -d db              # PostgreSQL on 127.0.0.1:55432 (override with DB_PORT)
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver # API on http://localhost:8000

# Frontend (second terminal)
cd frontend && npm ci && npm run dev # http://localhost:5173, proxies /api and /admin to :8000
```

Open **http://localhost:5173** during development (same-origin via the Vite proxy, so cookies and CSRF behave
like production). The service worker is only active in production builds: test PWA behaviour with
`npm run build` and then open http://localhost:8000 (Django serves `frontend/dist`).

## Quality checks (same as CI)

```bash
# Backend
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/pytest
# Frontend
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

## Translations

- Frontend texts: `frontend/src/locales/fr.json` and `en.json` (keys, no hard-coded strings in components).
- Backend texts (admin, API error messages): Django gettext in `locale/`
  (`manage.py makemessages -l fr -l en --ignore=.venv --ignore=tests --ignore=tools --ignore=frontend`).

## Configuration

All configuration comes from environment variables (see `.env.example`). With `DJANGO_DEBUG=false`
the app refuses to start without `DJANGO_SECRET_KEY` and enforces HTTPS, secure cookies and HSTS.
`GET /healthz` checks the database and is meant for hosting/monitoring probes.

## Docker image

```bash
docker build -t coachsurmesure .
docker run -p 8000:8000 -e DJANGO_SECRET_KEY=... -e DJANGO_ALLOWED_HOSTS=... -e DATABASE_URL=... coachsurmesure
```

Multi-stage build: Node builds the PWA, Python serves it. The container runs migrations on start, then
Gunicorn. Hosting provider (EU, possibly HDS) is decided in backlog `000023`.

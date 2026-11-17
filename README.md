# Coach sur mesure

Multi-coach fitness and nutrition platform for people with a West African background (France first, FR/EN).

- Product scope and quality bar: [`docs/definition-of-done.md`](docs/definition-of-done.md)
- Backlog: [`docs/backlogs/`](docs/backlogs/) — managed with `tools/backlog.py` (see `.claude/skills/backlog/SKILL.md`)

## Stack

Django 5.2 LTS · PostgreSQL 17 · server-rendered templates (HTMX later) · WhiteNoise · Gunicorn · Docker.
French is the default language (`/fr/…`), English is available (`/en/…`).

## Local setup (< 15 min)

Requirements: Python 3.13, Docker, gettext (`brew install gettext` on macOS).

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env                 # local values only, never commit .env
docker compose up -d db              # PostgreSQL on 127.0.0.1:55432 (override with DB_PORT)
.venv/bin/python manage.py migrate
.venv/bin/python manage.py compilemessages --ignore=.venv
.venv/bin/python manage.py runserver  # http://localhost:8000 -> /fr/
```

If you change `DB_PORT`, change the port in `DATABASE_URL` in `.env` too.

## Quality checks (same as CI)

```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/pytest
```

## Translations

```bash
.venv/bin/python manage.py makemessages -l fr -l en --ignore=.venv --ignore=tests --ignore=tools
# edit locale/fr/LC_MESSAGES/django.po (source strings in code/templates are English)
.venv/bin/python manage.py compilemessages --ignore=.venv
```

Rule: every user-facing string goes through `{% translate %}` / `gettext`; no hard-coded text.

## Configuration

All configuration comes from environment variables (see `.env.example`). With `DJANGO_DEBUG=false`
the app refuses to start without `DJANGO_SECRET_KEY` and enforces HTTPS, secure cookies and HSTS.
`GET /healthz` checks the database and is meant for hosting/monitoring probes.

## Docker image

```bash
docker build -t coachsurmesure .
docker run -p 8000:8000 -e DJANGO_SECRET_KEY=... -e DJANGO_ALLOWED_HOSTS=... -e DATABASE_URL=... coachsurmesure
```

The container runs migrations on start, then Gunicorn. Hosting provider (EU, possibly HDS) is decided in
backlog `000023`.

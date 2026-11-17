# Backlog: Project foundation: Django skeleton, i18n FR/EN, CI and staging

- **ID:** 000001
- **Slug:** project-foundation
- **Status:** open
- **Created:** 2026-11-17

## Summary

Set up the technical base every feature builds on, so login and onboarding can start on solid ground.
Confirms the recommended stack (Django + PostgreSQL + HTMX, installable PWA, EU hosting) as decision §5 #3 of the DoD.

## Reference

- docs/definition-of-done.md §1 (Item DoD), §2.7 (Quality & operations), §5 #3 (tech stack)
- Market analysis 2026-11-17: web-first PWA avoids app-store fees and a second codebase for the MVP

## Scope Hint

- Django project + apps layout, PostgreSQL, settings from environment (no secrets in repo)
- i18n: FR and EN locales, language switch, translation workflow (makemessages/compilemessages)
- Test setup (pytest or Django test runner), linter/formatter, CI pipeline running tests on every push
- Staging environment in the EU with synthetic data only; HTTPS; basic secure headers
- Git repository + .gitignore + README with local setup
- Out of scope: production environment (see ops-readiness), any user-facing feature

## Acceptance Hint

- `git clone` + documented steps start the app locally in < 15 min
- CI runs tests and linter green on main
- A sample page renders in FR and EN, language switch works
- Staging is reachable via HTTPS and deployed automatically from main

## Notes

Depends on: nothing. Tech-stack confirmation by product owner is part of this item.

### Progress (2026-11-17)

- Done: Django 5.2 LTS project (`config/`, `apps/core`, `apps/accounts` with custom user model before first
  migration), PostgreSQL via `DATABASE_URL` + docker-compose (port 55432), FR default / EN via `i18n_patterns`
  and language switch, `/healthz`, secure settings (`check --deploy` clean, HSTS preload deliberately off),
  pytest + ruff, CI workflow `.github/workflows/ci.yml`, production Dockerfile (smoke-tested locally), README,
  `git init` (no commit yet).
- Tech stack: product owner gave go-ahead to implement on Django (2026-11-17).
- Open before closing: (1) push to a remote so CI actually runs; (2) staging environment in the EU — blocked
  by hosting decision `000023-decision-hds-hosting` and access/credentials to a hosting account.

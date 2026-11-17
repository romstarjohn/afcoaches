# Observability rules

- **Status:** draft v0.1 (2026-11-17), to be confirmed by the product owner
- **Applies to:** every backlog item that adds or changes backend behaviour (referenced from the Item DoD in `definition-of-done.md` §1)
- **Code:** `apps/core/observability.py` (logging profiles, filters, JSON formatter), `apps/core/middleware.py` (request id, access log), `config/settings.py` (`DJANGO_ENV`, `LOG_DIR`)

## 1. Environments and where logs go

`DJANGO_ENV` is the dev/prod flag. It defaults to `prod`, so a forgotten variable fails safe. `DJANGO_DEBUG=true` is rejected unless `DJANGO_ENV=dev`.

| | `dev` | `prod` |
| --- | --- | --- |
| Format | text: `time LEVEL [request_id] logger: message` | JSON, one object per line |
| Level (own code `apps.*`) | DEBUG | INFO |
| Console | yes | yes (stdout is the primary signal for containers) |
| Files | `logs/dev/app.log`, `logs/dev/error.log` (ERROR+) | `logs/prod/app.log`, `logs/prod/error.log` (ERROR+) |
| Rotation | by size: 5 MB, 5 backups | daily at midnight (UTC), 14 backups |

- The directory is `<DJANGO_LOG_DIR or ./logs>/<dev|prod>/` and is created at startup. If it cannot be created, the app logs to the console only and prints a warning.
- `DJANGO_LOG_LEVEL` overrides the level. Third-party loggers stay at INFO; `django.db.backends` never goes below INFO because SQL parameters can contain personal or health data.
- `logs/` is git-ignored and docker-ignored. In production mount it as a volume or collect stdout; container filesystems are ephemeral.
- **Known limit:** Python's rotating handlers are not safe across several processes. With Gunicorn (`--workers 3`) rotation of the shared file is best-effort and can lose or misplace lines. Treat stdout as the source of truth in production and revisit with log shipping in backlog 000020 / the hosting decision.

## 2. Rules for every change

1. **Use the standard logger.** `logger = logging.getLogger(__name__)` at module level. No `print`, no custom handlers in feature code (lint enforces `print` and f-strings in log calls).
2. **Lazy formatting.** `logger.info("synced %s ops", count)`, never f-strings.
3. **Pick the level by who must act.**
   - `DEBUG`: developer detail, dev only.
   - `INFO`: normal business events and the per-request line (who/what/how long).
   - `WARNING`: unexpected but handled; user-caused problems that we want to count (sync conflicts, rejected operations, throttling).
   - `ERROR`: a request or job failed and someone should look. Always with the traceback (`logger.exception`).
   - `CRITICAL`: the service cannot work (database gone, configuration invalid).
4. **Never log personal or health data or secrets:** no emails, names, phone numbers, body weight, food entries, plan content, image data or file names, passwords, tokens, cookies, session ids, request bodies or query strings. Use stable IDs (`user_id`, `coach_id`, `op_id`) instead. `RedactFilter` masks obvious secrets as a safety net; it is not permission to log them.
5. **Structured context goes into `extra=`**, not into the message text: `logger.info("sync batch", extra={"coach_id": coach.pk, "applied": 12, "conflicts": 1})`. Keys must not collide with `LogRecord` attributes. Values are IDs and counts, never content.
6. **Correlation.** Every request gets an `X-Request-ID` (accepted from the client/proxy if it matches `[A-Za-z0-9._-]{8,64}`, otherwise generated). It is on every log line, including Django's own request warnings, and echoed in the response header. When a user reports a problem, ask for this id.
7. **Errors are handled once.** Log where you handle an exception, or let it propagate; do not log and re-raise at every layer. No silent `except: pass`; if swallowing is intended, log at WARNING or DEBUG with the reason.
8. **Tenant context.** Where an operation acts for a coach or client, include `coach_id` (and `user_id` when known) so incidents can be scoped to one tenant. Permission denials are logged at WARNING with IDs only.
9. **Sync and background paths** (the offline outbox, reminders later) log one summary line per batch or job: counts of applied/conflict/rejected, duration, and any failures. These are the signals that offline users are in trouble.
10. **Health and noise.** `/healthz` and static files log at DEBUG only. Do not add per-item INFO logs inside loops; log the aggregate.

## 3. Definition of "observable" for a backlog item

A backend item is observable when, before it is closed:

- [ ] A failure of the new behaviour produces an ERROR/WARNING line with enough context (IDs, request id, operation) to find the cause without reproducing it.
- [ ] The success path is visible: the request line or one INFO summary line.
- [ ] No personal or health data, secrets, query strings or bodies appear in logs (check a real log sample from a dev run).
- [ ] Permission failures and cross-tenant attempts are logged (WARNING, IDs only).
- [ ] If the item adds a new failure mode that should wake someone up in production, it is noted for the alerting list in backlog 000020 (e.g. "sync rejected rate > x%", "5xx rate", "healthz 503").
- [ ] New settings or env variables are documented in `.env.example`.

## 4. Review checklist (use in code review)

| Check | How |
| --- | --- |
| Logger usage | `grep -rn "print(" apps/` is empty; `getLogger(__name__)` used |
| Sensitive data | Read the new log calls and `extra=`; run the feature in dev and read `logs/dev/app.log` |
| Levels | Handled client errors are not ERROR; unexpected failures are not INFO |
| Exceptions | No bare `except` that hides errors; `logger.exception` used where handled |
| Context | IDs present (`coach_id`, `op_id`); no content |
| Tests | A test asserts the important log line or that the failure is logged (use `caplog`) |

## 5. Frontend and later extensions

- The PWA already shows sync state to the user (`SyncStatus`). Client-side error reporting, if added, must be same-origin (CSP is `connect-src 'self'`), scrubbed like server logs, and rate-limited.
- Metrics and tracing are not set up. When production monitoring is decided (backlog 000020 / hosting), start with request rate, error rate and duration per route derived from the request log line, plus the health probe. Do not add an APM vendor without a decision on cost, data location (EU) and lock-in.
- Log retention is a data-protection decision: keep local production logs no longer than needed (currently 14 days) and record it in the data inventory (DoD §2.6).

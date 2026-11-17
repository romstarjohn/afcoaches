# Architecture

- **Status:** decided 2026-11-17 by product owner (replaces the earlier Django-templates/HTMX recommendation)
- **Why:** the app is installed on phones and must let users **save data offline and sync on reconnect**.
  That needs client-side state (IndexedDB) and an API, i.e. a single-page app.

```
 Phone / browser (installed PWA)                         Server (one container, EU hosting)
┌───────────────────────────────────────┐   HTTPS    ┌──────────────────────────────────────┐
│ React SPA (frontend/)                  │  same      │ Django                                │
│  ├─ Service worker (Workbox)           │  origin    │  ├─ /api/v1/*   DRF, session + CSRF   │
│  │   precaches app shell only          │ ─────────► │  ├─ /admin/     staff back office     │
│  ├─ Dexie / IndexedDB                  │  cookies   │  ├─ /healthz    probe                 │
│  │   outbox of offline changes         │            │  └─ /*          SPA files (WhiteNoise)│
│  └─ SyncEngine → POST /api/v1/sync/push│            │ PostgreSQL                            │
└───────────────────────────────────────┘            └──────────────────────────────────────┘
```

## Decisions

| Topic | Decision | Reason |
|---|---|---|
| Frontend | React 19 + TypeScript + Vite, `frontend/` | Largest ecosystem for PWA/offline tooling, typed |
| PWA | `vite-plugin-pwa` (Workbox `generateSW`), `registerType: 'prompt'` | Standard tooling; never reload under a user with unsynced input |
| Hosting of SPA | Same origin as API, served by Django/WhiteNoise | Session cookies work, no CORS, one deployable |
| Auth | Django session cookie (HttpOnly, Secure, SameSite=Lax) + CSRF header | No tokens in JS-readable storage (XSS-safe); 30-day sliding session for offline use |
| API | Django REST Framework, JSON only, throttled, `IsAuthenticated` by default | Mature permission model for tenant isolation |
| Offline data | IndexedDB via Dexie; SW **never** caches `/api/` | Personal/health data stays under app control and is wiped on logout |
| Sync | Outbox + batch push (below); triggers: app start, `online`, foreground, every 60 s, manual retry | Background Sync API does not exist on iOS |
| Security headers | Strict CSP (`'self'` only, no inline script/style) on SPA; HSTS, nosniff, DENY framing | Limits XSS impact on health data |

## Sync contract (`POST /api/v1/sync/push`)

Request (max 100 operations):

```json
{ "operations": [
  { "op_id": "uuid", "entity": "feedback", "id": "uuid-of-record", "action": "upsert",
    "data": { "...": "..." }, "client_updated_at": "2026-11-17T10:00:00Z" } ] }
```

Response, one result per operation, in order:

```json
{ "results": [ { "op_id": "uuid", "status": "applied" | "conflict" | "rejected", "error": "code" } ] }
```

Rules:

1. **Client-generated UUIDs** for records → every write is idempotent; replays are safe.
2. Server handlers (`apps/sync/registry.py`) check permissions themselves and default to
   **last-write-wins on `client_updated_at`**. An older write arriving late is acknowledged as `applied`
   without changing newer data.
3. `applied` → client deletes the outbox item. `conflict`/`rejected` → item is kept as `failed` and shown to the
   user; never retried automatically. Network/5xx → exponential backoff (2 s … 5 min). 401/403 → keep
   everything, ask the user to log in again.
4. Several offline edits of the same record are **coalesced** into one operation; an edit made while the previous
   version is in flight gets a new `op_id` and is never lost.
5. Each operation runs in its own transaction; one bad operation never blocks the others.

New offline-capable entity = backend handler registered in the sync registry + Dexie table/schema version +
UI states (pending/failed) + tests. Read data needed offline (e.g. assigned plans) is cached in Dexie by the
feature, not by the service worker.

## Known limits

- iOS: no install prompt (hint shown instead), no Background Sync, web push only for installed PWAs (16.4+),
  storage may be evicted for rarely used non-installed sites → `navigator.storage.persist()` is requested.
- IndexedDB is not encrypted on the device. Keep offline data to what the user needs; wipe on logout
  (`clearLocalData()`); progress photos offline need an explicit decision (backlog 000015).
- Android splash screen uses the light `background_color` also in dark mode (manifest has no dark variant).

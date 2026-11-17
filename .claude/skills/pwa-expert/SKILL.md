---
name: pwa-expert
description: PWA engineering for this project (React + Vite + vite-plugin-pwa/Workbox, Dexie, Django/WhiteNoise hosting). Use for manifest, service worker, caching, install prompt, offline behaviour, sync and update flow. Activate on "PWA", "service worker", "offline", "install prompt", "manifest", "workbox", "sync". Not for visual design (use pwa-design) or native apps.
---

# PWA Expert (project-adapted)

Adapted from `curiositech/some_claude_skills` (`pwa-expert`). Removed: Next.js integration, foreign sample manifest, tool permissions. Added: project facts, iOS limits, Django hosting.

## Project facts (verify in code before relying on them)

- PWA shell: `frontend/` (React 19, Vite). Plugin: `vite-plugin-pwa` in `frontend/vite.config.ts`, Workbox `generateSW`. **Do not hand-write `sw.js`.**
- `registerType: 'prompt'`, registered from React (`virtual:pwa-register/react`); UI in `src/components/UpdatePrompt.tsx`. Never auto-reload while a user may hold unsynced input.
- Service worker caches the **app shell only** (`runtimeCaching: []`). API responses are **never** cached by the SW: personal and health data lives in IndexedDB (Dexie, `src/offline/`) under app control so it can be wiped on logout. Keep it that way unless the product owner decides otherwise (GDPR).
- `navigateFallbackDenylist` excludes `/api/`, `/admin/`, `/static/`, `/healthz`. Add every new non-SPA route there.
- Offline writes: outbox pattern in `src/offline/outbox.ts` / `sync.ts`, status in `src/components/SyncStatus.tsx`.
- Hosting: Django + WhiteNoise serves `frontend/dist` from the site root (see `SPA_DIST_DIR` in `config/settings.py`). `/sw.js` must be served from `/` (scope), with revalidation, never long-cached; hashed `/assets/*` may be immutable.
- Icons come from `public/logo.svg` via `pwaAssets` (`minimal-2023` preset). Change the source SVG, not generated PNGs.

## Installability checklist

HTTPS (localhost in dev) · manifest with `name`, `short_name`, `start_url`, `scope`, `display: standalone`, `id` · 192 and 512 px icons plus a maskable icon · service worker with fetch handling · `theme_color` / `background_color` matching the tokens in `src/index.css` (light and dark).

## Caching strategies

| Strategy | Use for | In this project |
| --- | --- | --- |
| Precache (Workbox) | App shell, hashed assets, fonts | Yes (default) |
| Network-only | Auth, API, personal/health data | Yes: API is never SW-cached |
| Stale-while-revalidate | Public, non-personal images | Only if added deliberately and reviewed |
| Cache-first | Immutable versioned files | Covered by precache |

## Install prompt

`beforeinstallprompt` exists in Chromium only. **iOS Safari has no install prompt**: show a short "Share → Add to Home Screen" hint (FR and EN) instead, only when not already standalone (`matchMedia('(display-mode: standalone)')` or `navigator.standalone`). Never block content behind an install prompt; show it after the user has experienced value, and respect a dismissal.

## Offline and sync

- **Background Sync API is Chromium-only (no iOS/Safari).** Do not depend on it. Sync from the outbox on app start, on `online` events, on `visibilitychange` to visible, and via manual retry; treat Background Sync as an optional enhancement.
- Show offline state and pending/failed sync in the UI (see `pwa-design`); never silently drop outbox entries.
- Outbox operations must be idempotent (client-generated IDs) so retries cannot duplicate data.
- On logout: clear IndexedDB personal data and any caches that could hold it.
- iOS may evict storage for rarely used PWAs; treat local data as a cache of server state, not the source of truth, unless an item says otherwise.

## Update flow

Detect new worker via the plugin's `onNeedRefresh`; ask the user, flush or preserve the outbox, then update. Avoid `skipWaiting()`/`clients.claim()` shortcuts that swap the shell under an active session.

## iOS specifics

`apple-mobile-web-app-capable`, `apple-mobile-web-app-title` and `viewport-fit=cover` are set in `index.html`. If a translucent status bar is ever used, content runs under it: handle safe areas (see `pwa-design`). Push notifications on iOS work only for installed PWAs (16.4+) and need user permission triggered by a user gesture; reminders (backlog 000016) must not assume push is available.

## Testing

DevTools → Application (Manifest, Service Workers, Storage) · Network → Offline · Lighthouse PWA/installability · test on real iOS Safari and Android Chrome (Definition of Done §1) · test update flow with an old build installed · test logout wipes local data.

## Debug checklist

- [ ] Manifest loads and is valid
- [ ] SW registered, scope `/`, served with revalidation
- [ ] Shell loads offline; `/api/` requests fail cleanly (not served from cache)
- [ ] Outbox syncs after reconnect, no duplicates
- [ ] Update prompt appears for a new build and does not lose input
- [ ] Logout clears personal data

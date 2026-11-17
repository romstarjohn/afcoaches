---
name: pwa-design
description: Visual and interaction design rules for this project's mobile-first installed PWA (safe areas, touch targets, standalone mode, offline/sync states, dark mode, FR/EN text length, accessibility). Use when designing or reviewing any screen, component or CSS in frontend/. Complements frontend-design (aesthetic direction) and emil-design-eng (motion).
---

# PWA Visual Design (project-specific)

Origin: written for this repo from observed code (`frontend/src/index.css`, `index.html`, `vite.config.ts`) and `docs/definition-of-done.md`. No brand guideline exists yet (not found in repo): treat colors and type below as the current baseline, not a final identity. Ask the product owner before inventing brand decisions.

## Audience and context

West African diaspora in France, FR default and EN, mostly phone use, often in gyms and kitchens: one hand, bright or dim light, unstable connectivity. Coaches also use desktop. Design mobile first at 360 px; verify on desktop and on iOS Safari and Android Chrome.

## Precedence between the design skills

The skills can pull in different directions: `frontend-design` pushes for distinctive, risk-taking aesthetics; this skill favours familiarity and reliability.

- **Everyday screens** (logging a workout, meal, check-in; plan views; forms; lists; settings): this skill wins. Use familiar patterns, restrained decoration, predictable navigation. Users repeat these tasks often and one-handed.
- **Brand and first-impression surfaces** (landing, onboarding, empty states, coach profile header, public plan cards): `frontend-design` may lead for aesthetic direction, within the constraints below.
- **Hard constraints always win over aesthetics:** accessibility and contrast, safe areas, touch targets, offline states, FR/EN text length, performance, CSP (no inline styles), existing tokens.
- **Motion:** follow `emil-design-eng`; frequent actions get little or no animation.
- **Open conflict:** if two skills disagree and the rule above doesn't settle it, say so and ask the product owner rather than choosing silently.

## Existing baseline (reuse, don't parallel-build)

- Tokens in `:root` of `src/index.css`: brand `--brand --brand-fg` (dark blue), action `--accent --accent-fg` (green), `--accent-on-brand(-fg)` (lighter green for elements on the dark-blue header), `--bg --surface --fg --muted --border --ok --warn --offline`, shape `--radius --radius-sm`, with a `prefers-color-scheme: dark` set. Extend these; no hard-coded hex in components.
- Type scale tokens (native app conventions, Material 3 / iOS HIG, in rem): `--text-caption` 12 · `--text-footnote` 13 · `--text-label` 14 · `--text-body` 16 (17 on iOS via Dynamic Type `font: -apple-system-body`) · `--text-title` 20 · `--text-title-lg` 22 (app bar) · `--text-headline` 28. Use the tokens, never px font sizes; inputs and buttons use `--text-body`.
- **No inline styles / `style` attributes in markup:** CSP allows `style-src 'self'` only. Use classes.
- Font: system stack. Adding a webfont costs performance and offline precache size; justify it first (self-host, `woff2`, `font-display: swap`).
- Colors decided by product owner 2026-11-17: **dark blue + green**. Manifest `theme_color` `#0b2a4a` = `--brand` (light), dark-mode meta theme-color `#0d1c30`; `background_color` `#f5f8fb` = `--bg`. Keep manifest, `index.html`, `public/logo.svg` and tokens in sync.
- Green on the dark-blue header: use `--accent-on-brand` (the regular `--accent` fails 3:1 there).

## Layout and safe areas

- `viewport-fit=cover` is on, so handle all four insets: `env(safe-area-inset-top|bottom|left|right)`. The header already pads top; fixed bottom bars and full-bleed elements must pad bottom (home indicator) and landscape sides.
- Use `100dvh`, not `100vh`.
- Primary navigation and primary actions in the thumb zone (bottom) on mobile; a standalone PWA has no browser back button, so provide in-app back/close affordances on every non-root screen.
- Content max width ~960 px on desktop; readable line length under ~75 characters.
- Prevent overscroll surprises: be deliberate with `overscroll-behavior` on drawers and modals.

## Touch and input

- Targets at least 44×44 px with 8 px spacing (existing `.lang-switch__btn` sets the pattern).
- Inputs at 16 px font size or larger (smaller triggers iOS zoom). Use correct `inputmode`, `autocomplete`, `type` (numeric keypad for weight, reps, kcal).
- Don't rely on hover; no hover-only information. Gate hover effects with `(hover: hover) and (pointer: fine)`.
- Forms: labels always visible, errors say what to fix, preserve entered data on failure and when offline.

## Offline, sync and update states (first-class UI)

Every data screen needs designed states, not afterthoughts:

| State | Treatment |
| --- | --- |
| Online, synced | Quiet (small dot, see `SyncStatus`) |
| Offline | Persistent but calm banner/indicator; action buttons still work and say "saved on this device" |
| Pending sync | Per-item "pending" marker, never a blocking spinner |
| Sync failed | Clear message + retry; entry is never lost |
| Update available | `UpdatePrompt`: non-blocking, user-timed |
| Empty | Say what to do next, offer the action |
| Loading | Skeleton matching final layout; avoid layout shift |

Do not communicate state by color alone (`--ok`/`--warn`/`--offline` need icon or text too).

## Standalone mode

- Don't show "install" UI when already standalone. iOS has no install prompt: use a one-time FR/EN hint ("Share → Add to Home Screen").
- Splash/background color = `background_color`; avoid a white flash in dark mode (check `theme_color`/`background_color` for dark scheme).
- External links open in the browser; make it clear when leaving the app.

## Color, dark mode, contrast

- Text contrast at least 4.5:1 (3:1 for large text and UI components), in light and dark. Verify `--accent` on `--bg` and `--accent-fg` on `--accent` whenever tokens change.
- Dark mode is first-class, not inverted light mode: test images, charts, shadows, borders.
- Charts (weight trends, adherence): do not rely on color alone; label values; make them readable at 360 px. Use the `dataviz` skill for chart work.
- Images (food, progress photos, user uploads): reserve aspect ratio, lazy-load, handle missing/slow; progress photos are sensitive, avoid showing them in previews or notifications by default.

## Internationalization

- FR strings run ~20–30% longer than EN: no fixed-width buttons or truncation of key labels; test every screen in both languages.
- No hard-coded strings (Definition of Done §1); date, number, decimal comma and unit formatting via `Intl` per locale.
- Food names: West African dish names and diacritics must render correctly; don't uppercase or truncate them.
- Tone: plain, respectful, sentence case, active verbs; reuse the same action name through a whole flow.

## Accessibility (baseline for every screen)

Visible keyboard focus · semantic HTML (buttons are buttons) · labelled inputs · `aria-live` for sync/offline/error announcements · `prefers-reduced-motion` respected · page zoom to 200% without breaking · screen-reader check on core flows.

## Performance as design

Fast first paint matters on mid-range Android over mobile data: small images (responsive `srcset`, modern formats), no layout shift, restrained JS per route, no heavy libraries for small effects.

## Review checklist

| Check | Pass condition |
| --- | --- |
| 360 px width | No horizontal scroll, targets ≥ 44 px |
| Safe areas | Top, bottom and sides handled |
| Standalone | In-app back; no install UI when installed |
| Offline | Shell loads; states from the table above exist |
| Dark mode | Contrast verified, no white flash |
| FR and EN | No overflow or truncation |
| Inputs | 16px+, correct keyboards, data kept on error |
| Tokens | No hard-coded colors, no inline styles |
| Motion | Follows `emil-design-eng`; reduced motion handled |
| Aesthetic | Passes the `frontend-design` self-critique |

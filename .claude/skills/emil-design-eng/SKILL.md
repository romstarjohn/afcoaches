---
name: emil-design-eng
description: UI polish, motion and interaction rules (animation decisions, easing, press feedback, performance, reduced motion). Use when building or reviewing animations, transitions, buttons, popovers, drawers, toasts or touch interactions. Based on Emil Kowalski's design engineering philosophy (animations.dev).
---

# Design Engineering (motion & interaction polish)

Scope: how an interface *feels*. It does not cover layout, typography, color or brand — use the `frontend-design` skill for that.

Project context: React + Vite PWA, plain CSS (no Framer Motion, no Radix). Prefer CSS transitions and the Web Animations API. Only add an animation library if a requirement (e.g. gesture physics) can't be met otherwise.

The rules below are strong defaults, not laws. Deviate when there is a reason and say why.

## Principles

- **Taste is trained.** Study why good interfaces feel good; don't just make it work.
- **Unseen details compound.** Users don't notice correct details; they notice missing ones.
- **Good defaults beat options.** Most people never customize easing, timing or styling.

## Review format

When reviewing UI code, output one markdown table, one row per issue:

| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 200ms var(--ease-out)` | Name exact properties; avoid `all` |
| `transform: scale(0)` | `transform: scale(0.95); opacity: 0` | Nothing appears from nothing |
| `ease-in` on dropdown | `ease-out` custom curve | `ease-in` feels sluggish at the moment the user watches most closely |
| No `:active` state on button | `transform: scale(0.97)` on `:active` | Pressable elements must acknowledge the press |

## Animation decision framework

Answer in order before writing animation code.

### 1. Should it animate at all?

| How often users see it | Decision |
| --- | --- |
| 100+ times/day (keyboard shortcuts, command palette) | No animation |
| Tens of times/day (hover, list navigation) | Remove or drastically reduce |
| Occasional (modals, drawers, toasts) | Standard animation |
| Rare / first-time (onboarding, celebrations) | Can add delight |

Never animate keyboard-initiated actions.

### 2. What is the purpose?

Valid: spatial consistency (enter/exit from the same side), state indication, explanation, feedback (press), softening jarring appear/disappear. If the purpose is only "looks cool" and users see it often, don't animate.

### 3. Which easing?

- Entering/exiting → `ease-out`
- Moving/morphing on screen → `ease-in-out`
- Hover / color change → `ease`
- Constant motion (progress, marquee) → `linear`
- Default → `ease-out`

Built-in CSS easings are weak; use custom curves:

```css
:root {
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
  --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
}
```

Avoid `ease-in` for UI: it delays the initial movement, so the same duration feels slower. Resources: easing.dev, easings.co.

### 4. How fast?

| Element | Duration |
| --- | --- |
| Button press feedback | 100–160ms |
| Tooltips, small popovers | 125–200ms |
| Dropdowns, selects | 150–250ms |
| Modals, drawers | 200–500ms |
| Marketing / explanatory | can be longer |

Keep ordinary UI animations under ~300ms. Faster feels more responsive; a quick spinner makes loading feel faster at identical load time. Exit should be faster than enter.

## Springs

Use for drag with momentum, interruptible gestures, and decorative "alive" elements. Not for functional data displays. Keep bounce subtle (0.1–0.3) or none. Springs preserve velocity when interrupted; keyframes restart from zero.

## Component rules

- **Pressable elements:** `transform: scale(0.97)` on `:active` (range 0.95–0.98), 100–160ms `ease-out`.
- **Entrances:** never from `scale(0)`; start at `scale(0.95)` + `opacity: 0`.
- **Popovers:** `transform-origin` at the trigger, not center. Modals stay centered.
- **Tooltips:** delay on first hover; when one is open, adjacent tooltips open instantly with no animation.
- **Transitions over keyframes** for anything triggered rapidly (toasts, toggles): transitions retarget mid-flight, keyframes restart.
- **Blur masks imperfect crossfades:** add `filter: blur(2px)` during the swap; keep blur under 20px (expensive in Safari).
- **Entry without JS:** `@starting-style { opacity: 0; transform: translateY(100%); }`; fall back to a `data-mounted` attribute if browser support is insufficient.
- **Stagger:** 30–80ms between items, decorative only, never block interaction.
- **Asymmetric timing:** slow where the user is deciding (hold-to-confirm), fast where the system responds (release 200ms `ease-out`).

## Transforms and clip-path

- `translateY(100%)` moves an element by its own height; prefer percentages over hard-coded pixels.
- `scale()` scales children too (usually desired on press).
- `clip-path: inset(...)` is a strong animation tool: reveals, hold-to-delete overlays, tab color transitions (duplicate the tab list, clip the active copy), comparison sliders.

## Gestures and drag

- Dismiss on velocity, not only distance: `|distance| / elapsedMs > ~0.11` dismisses.
- Damp at boundaries (friction instead of hard stops).
- Capture the pointer once dragging starts (`setPointerCapture`).
- Ignore additional touch points after a drag begins.
- Test touch interactions on a real device.

## Performance

- Animate only `transform` and `opacity`; avoid `width`, `height`, `margin`, `padding`.
- CSS animations run off the main thread and stay smooth while the page loads; JS animation can drop frames. Use CSS for predetermined motion, JS/WAAPI for dynamic, interruptible motion.
- Don't update inherited CSS variables per frame on a parent with many children; set `transform` on the element directly.
- Web Animations API gives JS control with CSS performance: `element.animate(keyframes, { duration, fill: 'forwards', easing })`.

## Accessibility

- `prefers-reduced-motion: reduce`: fewer and gentler, not zero. Keep opacity/color changes that aid comprehension; remove movement and position animation.
- Gate hover effects: `@media (hover: hover) and (pointer: fine)`. Touch devices fire hover on tap.

## Cohesion and verification

Match motion to the product's mood: crisp and fast for tools, softer for playful brands. Verify by playing animations at 2–5× duration (DevTools Animations panel) and frame by frame; look for overlapping states, wrong `transform-origin`, out-of-sync properties. Review again the next day.

## Review checklist

| Issue | Fix |
| --- | --- |
| `transition: all` | List exact properties |
| `scale(0)` entrance | `scale(0.95)` + `opacity: 0` |
| `ease-in` on UI | `ease-out` or custom curve |
| Popover with `transform-origin: center` | Origin at trigger (modals exempt) |
| Animation on keyboard action | Remove |
| Duration > 300ms on ordinary UI | 150–250ms |
| Hover animation without media query | Add `(hover: hover) and (pointer: fine)` |
| Keyframes on rapidly triggered element | Use transitions |
| Same enter and exit speed | Make exit faster |
| Everything appears at once | Stagger 30–80ms |
| No reduced-motion handling | Add `prefers-reduced-motion` fallback |

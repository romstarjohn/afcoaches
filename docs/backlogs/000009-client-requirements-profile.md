# Backlog: Client requirements profile with versioned history

- **ID:** 000009
- **Slug:** client-requirements-profile
- **Status:** open
- **Created:** 2026-11-17

## Summary

The coach-maintained profile per client (goals, targets, level, availability, restrictions, preferences) that
plans and the client summary build on. Pre-filled from onboarding standard fields.

## Reference

- docs/definition-of-done.md §2.1 (client requirements profile, versioned), §2.4 (pre-fill from standard fields), §2.6 (religion-revealing dietary data)

## Scope Hint

- Profile model and coach UI; pre-fill from latest onboarding answers via standard field keys; coach confirms
- Every change versioned (who, when, old -> new) with history view
- Custom-field answers shown as "Additional information"
- Client is notified when requirements change
- Dietary pattern stored only as client-chosen preference (special category)

## Acceptance Hint

- Pre-fill maps every standard field correctly (tests)
- History shows all changes; client notified

## Notes

Depends on: onboarding-client-flow.

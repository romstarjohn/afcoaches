# Backlog: Reminders and notifications engine

- **ID:** 000016
- **Slug:** reminders-notifications
- **Status:** open
- **Created:** 2026-11-17

## Summary

Prompt only clients to give feedback according to the coach-defined rhythm, via in-app, email and web push,
respecting client channel choice and quiet hours.

## Reference

- docs/definition-of-done.md §2.1 (feedback rhythm per client), §2.3 (prompts, channels, quiet hours, max 1 reminder per item)

## Scope Hint

- Coach sets rhythm per client (after workout, daily meals, weekly check-in day)
- Scheduler for due items; in-app badge, email, web push (PWA installed + permission; iOS limitation documented)
- Client preferences: channel, quiet hours; max 1 reminder per due item
- Never sent to followers; stop immediately when relationship ends or consent withdrawn
- Also notifications: plan assigned, requirements changed, coach comment

## Acceptance Hint

- No reminder ever reaches a follower (tests)
- Quiet hours respected; no duplicates

## Notes

Depends on: client-feedback-images.

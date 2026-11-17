# Backlog: Client summary dashboard and requirement updates

- **ID:** 000017
- **Slug:** client-summary-dashboard
- **Status:** open
- **Created:** 2026-11-17

## Summary

Rule-based summary per client so the coach can adjust requirements and plans without chasing the client on
WhatsApp: adherence, trends, latest feedback, image timeline, attention flags.

## Reference

- docs/definition-of-done.md §2.1 (client summary, flags, <= 2 clicks to update), §3 (pilot: adjust without phone/WhatsApp), §5 #7, #9

## Scope Hint

- Adherence last 7/28 days, weight/effort trends (charts), latest notes, image timeline
- Attention flags: no feedback > N days, adherence below threshold, pain/injury note, screening flag
- Coach overview list of all clients sorted by flags
- Update requirements / adjust or reassign plans in <= 2 clicks; client notified
- No AI (deferred to post-pilot)

## Acceptance Hint

- Pilot coach completes a weekly review of 10 clients faster than before (measured)
- Flag thresholds configurable per coach

## Notes

Depends on: client-feedback-images, client-requirements-profile, reminders-notifications.

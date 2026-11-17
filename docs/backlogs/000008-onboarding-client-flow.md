# Backlog: Onboarding: client questionnaire flow, screening flags and re-send

- **ID:** 000008
- **Slug:** onboarding-client-flow
- **Status:** open
- **Created:** 2026-11-17

## Summary

Clients fill the coach's questionnaire on mobile after consent; screening answers raise attention flags; coaches
can re-send it periodically. Target: >= 80 % completion, median <= 10 minutes.

## Reference

- docs/definition-of-done.md §2.4 (behaviour), §3 (completion targets)

## Scope Hint

- Questionnaire sent automatically after invitation accepted + consent; never to followers
- Mobile-first stepper, autosave, resume later; status for coach (sent / in progress / completed)
- Screening "yes" -> client notice "medical clearance recommended" + coach attention flag (no diagnosis, no block)
- Answers bound to questionnaire version; re-send creates a new answer version with highlighted changes
- Track completion time (for pilot metrics)
- Reminders: simple email reminder here; full reminder engine comes with reminders-notifications

## Acceptance Hint

- Standard template completable in <= 10 min in a usability test with 3 people
- Followers and other coaches cannot read answers (tests)
- Re-send keeps history; changes visible

## Notes

Depends on: onboarding-coach-questionnaire-builder, client-invitation-consent.

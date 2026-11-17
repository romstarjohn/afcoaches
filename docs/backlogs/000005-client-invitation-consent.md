# Backlog: Client invitation, coaching relationship and Art. 9 consent

- **ID:** 000005
- **Slug:** client-invitation-consent
- **Status:** open
- **Created:** 2026-11-17

## Summary

Turn a person into a client of a coach with explicit, separate, withdrawable consent for health data and a
separate photo opt-in. Onboarding and all feedback features require this relationship and consent.

## Reference

- docs/definition-of-done.md §2.1 (invite client, end relationship), §2.3 (consent before first feedback, photo opt-in), §2.6 (Art. 9)

## Scope Hint

- Coach invites by email (new or existing user); accept/decline flow
- CoachingRelationship model with status (invited, active, ended) and history
- Consent records: health-data consent and photo opt-in, versioned consent text, timestamp, withdrawal
- Ending a relationship: client falls back to follower; feedback and reminders stop immediately
- Out of scope: data deletion jobs after withdrawal (see gdpr-self-service)

## Acceptance Hint

- No client-only feature is reachable without active relationship + health consent (tests)
- Photo upload blocked without photo opt-in (tests)
- Consent withdrawal is possible in <= 2 clicks and logged

## Notes

Depends on: coach-discovery-follow. Consent texts need legal review (see legal-compliance-docs).

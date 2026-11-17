# Backlog: GDPR self-service: data export, account deletion and retention jobs

- **ID:** 000018
- **Slug:** gdpr-self-service
- **Status:** open
- **Created:** 2026-11-17

## Summary

Users exercise their rights themselves, and retention rules delete feedback and images automatically.

## Reference

- docs/definition-of-done.md §2.6 (export, deletion Art. 15/17/20, retention proposal 12 months), §2.3 (consent withdrawal deletes data), §5 #8

## Scope Hint

- Data export (JSON + images ZIP) for any user
- Account deletion with confirmation; cascade incl. images in storage
- Consent withdrawal triggers deletion per rules
- Scheduled retention job (12 months after relationship end, to be confirmed)

## Acceptance Hint

- Export contains all personal data of the user (tested against data inventory)
- After deletion no personal data or images remain (tests incl. storage)

## Notes

Depends on: client-feedback-images.

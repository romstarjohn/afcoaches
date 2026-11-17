# Backlog: Client activity feedback, check-ins and secure image storage

- **ID:** 000015
- **Slug:** client-feedback-images
- **Status:** open
- **Created:** 2026-11-17

## Summary

Clients report on planned training days and meals (status, effort, note, up to 3 images) and do periodic
check-ins with progress photos. Images are the most sensitive data of the platform.

## Reference

- docs/definition-of-done.md §2.3 (feedback, check-in, <= 30 s, edit 24 h), §2.6 (private EU bucket, signed URLs, EXIF strip, retention)

## Scope Hint

- Feedback per plan item/day: done/partial/skipped, effort 1-10, note, <= 3 images
- Periodic check-in: weight, measurements, wellbeing, photos, note
- Image pipeline: type/size validation, EXIF/GPS strip, private EU bucket, short-lived signed URLs after permission check
- Client history, edit within 24 h, delete images anytime; coach one-way comments
- Only client + current coach can access

## Acceptance Hint

- Simple feedback in <= 30 s on mobile
- EXIF removed (test with GPS-tagged sample), no public URLs (tests)
- Access denied for followers, other coaches, former coach (tests)

## Notes

Depends on: plan-visibility-assignment-feed, client-invitation-consent. Hosting choice depends on decision-hds-hosting.

Offline: feedback and check-ins must work offline via the sync contract in `docs/architecture.md` (register a
sync handler, Dexie table, pending/failed UI). Decide whether photos are stored offline (IndexedDB is not
encrypted).

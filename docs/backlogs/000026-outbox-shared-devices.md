# Backlog: Offline outbox on shared devices

- **ID:** 000026
- **Slug:** outbox-shared-devices
- **Status:** open
- **Created:** 2026-11-17

## Summary

Make sure unsent offline data of one person can never be sent under another person's account when two people
use the same phone, and that logging out does not leave personal data behind on the device.

## Reference

- frontend/src/offline/ (Dexie outbox, SyncEngine), frontend/src/auth/ (login, logout), docs/architecture.md (sync contract)
- docs/definition-of-done.md §2.6, §2.8

## Scope Hint

- Tag every outbox entry with the account (user id) that created it
- The sync engine only sends entries of the currently signed-in account; entries of others stay untouched
- On logout: warn when unsent changes exist; offer to keep them (resume after next login of the same person) or to delete them
- Cached data and the cached profile of the previous account are removed on logout or account change
- Out of scope: encrypting local storage

## Acceptance Hint

- Test: user A leaves unsent entries, logs out, user B logs in: nothing of A is sent as B
- Test: A logs in again and the entries are still there and get synced
- Test: logout with unsent entries shows the warning
- No personal data of the previous account remains in IndexedDB/localStorage after the chosen delete option

## Deferral Context

### Deferred From

docs/backlogs/000002-auth-registration-login.md (frontend login/logout, step 7a)

### Defer Reason

Harmless today: no feature writes real data through the outbox yet. It must be solved before the first real sync
handler (feedback, check-ins, photos) ships.

### Findings

The outbox belongs to the device, not to the account. After logout the SyncEngine still holds unsent entries and
would send them with whichever session is active next. The signed-out state also keeps a cached profile in
localStorage (csm.user) until the next server answer.

### Direction Hint

Do this together with or before the first sync handler (see 000012, 000013, 000015). Prefer tagging entries with the
user id over wiping on every logout: wiping would lose a person's offline work after an accidental logout.

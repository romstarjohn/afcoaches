# Backlog: Roles and coach accounts with admin activation and tenant isolation

- **ID:** 000003
- **Slug:** roles-coach-accounts-tenant-isolation
- **Status:** open
- **Created:** 2026-11-17

## Summary

Introduce the coach role, admin activation of coaches and the permission layer that guarantees a coach can never
access another coach's data. Built before any coach data exists so isolation is a foundation, not a retrofit.

## Reference

- docs/definition-of-done.md §2.1 (coach registration, verified/activated by admin, public profile; tenant isolation tests for every endpoint)

## Scope Hint

- Coach application flow on top of auth; platform admin activates/deactivates coaches (Django admin)
- Coach public profile: photo, bio, specialties, languages
- Central permission helpers / querysets scoped by coach ("tenant"), reusable test helpers that assert
  other-coach / follower / anonymous access is denied
- Out of scope: clients, follow, plans

## Acceptance Hint

- Non-activated coach cannot access coach area
- Reusable isolation test helper exists and is used by all coach endpoints
- Public coach profile visible in FR/EN

## Notes

Depends on: auth-registration-login.

# Backlog: Authentication: registration, login, email verification, password reset

- **ID:** 000002
- **Slug:** auth-registration-login
- **Status:** open
- **Created:** 2026-11-17

## Summary

Secure account system for all roles. Registration must stay in <= 3 steps (DoD §2.2) because followers sign up
casually from a coach's content; every later feature depends on a trustworthy identity.

## Reference

- docs/definition-of-done.md §2.2 (follower registration <= 3 steps), §2.6 (hashed passwords, login rate-limiting, HTTPS)

## Scope Hint

- Custom user model from day one (email as login, display name, preferred language FR/EN)
- Registration (email + password), email verification, login/logout, password reset, change email/password
- Rate limiting / lockout on login and reset; generic error messages (no account enumeration)
- Session security settings (secure cookies, CSRF), password validators
- New accounts default to role "member" (= can follow); coach/client roles come later
- Out of scope: social login (Google/Apple) -> separate later item if needed; 2FA

## Acceptance Hint

- Registration to first logged-in screen in <= 3 steps on mobile
- Unverified emails cannot log in (or are restricted) as defined
- Tests: registration, verification, login, lockout after N failures, reset flow, no enumeration
- All texts FR/EN

## Notes

Depends on: project-foundation.

# Backlog: Production readiness: PWA, performance, accessibility, backups, security review

- **ID:** 000020
- **Slug:** production-readiness
- **Status:** open
- **Created:** 2026-11-17

## Summary

Everything required to put real users on the platform safely.

## Reference

- docs/definition-of-done.md §2.6 (security review, dependency audit), §2.7 (PWA, LCP < 2.5 s, WCAG 2.1 AA basics, rollback, backups, monitoring, runbook)

## Scope Hint

- PWA manifest/service worker, installable on iOS/Android
- Performance budget (LCP < 2.5 s mid-range phone/4G); accessibility check of core flows
- Production environment in EU; automated deploy; rollback tested once
- Daily backups; restore tested once; monitoring/alerting; no personal data in logs
- Dependency audit; external/peer security review of auth, permissions, tenant isolation; fix findings
- Admin runbook

## Acceptance Hint

- All §2.6 and §2.7 checkboxes of the DoD ticked

## Notes

Depends on: all feature items.

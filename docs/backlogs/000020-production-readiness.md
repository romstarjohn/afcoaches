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

- PWA manifest/service worker already in place (000001); verify installability and offline shell on real devices
- Performance budget (LCP < 2.5 s mid-range phone/4G); accessibility check of core flows
- Production environment in EU; automated deploy; rollback tested once
- Daily backups; restore tested once; monitoring/alerting; no personal data in logs
- Dependency audit; external/peer security review of auth, permissions, tenant isolation; fix findings
- Mail worker (`manage.py send_mail_outbox`, apps/mailer) runs in production as its own process/container with the
  same image; alert when mails end up `failed` or the queue keeps growing (from 000002)
- Login lockout counters and the other rate limits use a cache shared by all web processes (today: local memory of
  each process, so with several workers the limits are weaker than configured)
- Admin runbook

## Acceptance Hint

- All §2.6 and §2.7 checkboxes of the DoD ticked
- With two web processes, five failed logins in total lock an account (not five per process)
- A stopped mail worker triggers an alert; mails queued meanwhile are sent after it restarts

## Notes

Depends on: all feature items. Email provider and DNS: 000025. Hosting: 000023.

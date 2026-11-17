# Backlog: Email provider, sender address and DNS

- **ID:** 000025
- **Slug:** email-provider-sender-dns
- **Status:** open
- **Created:** 2026-11-17

## Summary

Choose who sends the platform's emails and from which address, and set up the sending domain so that
verification, password-reset and notification mails arrive in the inbox and not in spam.

## Reference

- apps/mailer (outbox + worker), apps/accounts/emails.py, config/settings.py (EMAIL_*, DJANGO_SITE_URL)
- docs/definition-of-done.md §2.6 (GDPR, no personal data leaks)
- Related: 000020-production-readiness, 000023-decision-hds-hosting

## Scope Hint

- Decision (product owner): email provider with EU servers and a data processing agreement (AVV/DPA); sender
  name and address; a contact address for replies
- DNS records on the sending domain: SPF, DKIM, DMARC (start with a monitoring-only DMARC policy)
- Configure the provider through the existing DJANGO_EMAIL_* variables and DJANGO_FROM_EMAIL (no secrets in the repo)
- Set DJANGO_SITE_URL to the final public address (links in emails use it)
- Bounces/complaints: decide whether the provider's handling is enough for transactional mail
- Out of scope: marketing/newsletters, reminder content (see 000016)

## Acceptance Hint

- A real test mail (verification and password reset) reaches inboxes at the major providers, not the spam folder
- SPF, DKIM and DMARC checks pass for the sending domain
- Provider contract (AVV/DPA) in place and recorded in the data inventory
- Emails contain no health data

## Deferral Context

### Deferred From

docs/backlogs/000002-auth-registration-login.md (email verification, password reset, password/email change)

### Defer Reason

Needs decisions only the product owner can make (provider, sender, domain) and DNS access. The auth item works
end to end with the console backend and the test backend, so it was not blocked.

### Findings

Mails are queued in the database and sent by a separate worker with retries (apps/mailer), so switching provider
only means changing the DJANGO_EMAIL_* settings. Without SPF/DKIM/DMARC, verification and reset mails are likely
to land in spam, which would block registration in practice. Mail bodies contain names and links only, never
health data; keep it that way.

### Direction Hint

Prefer an EU provider with a signed AVV. Avoid provider-specific APIs: keep plain SMTP so the provider can be
swapped without code changes. Do this before the pilot launch (000021).

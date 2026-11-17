# Backlog: Onboarding: coach questionnaire builder with inherited and custom fields

- **ID:** 000007
- **Slug:** onboarding-coach-questionnaire-builder
- **Status:** open
- **Created:** 2026-11-17

## Summary

Coaches get a questionnaire created from the platform standard template and can adapt it: hide optional standard
fields, reorder, adjust help texts and add custom fields at any time.

## Reference

- docs/definition-of-done.md §2.4 (coach layer, cannot change type/meaning of standard fields, mandatory fields, adoption of new template versions, data-minimisation hint)

## Scope Hint

- Coach questionnaire created automatically from current standard template on coach activation
- Hide optional standard fields, reorder, edit help text; mandatory fields (screening, consent) locked
- Add/edit/remove custom fields with all field types; data-minimisation hint; image fields require photo opt-in
- Every edit creates a new questionnaire version
- Notification + "adopt new standard fields" when the platform template gets a new version
- Out of scope: client filling flow

## Acceptance Hint

- Pilot coach can add a custom field without developer help (DoD §3)
- Editing never changes existing answers (tests)
- Coach cannot change type/key of standard fields (tests)

## Notes

Depends on: onboarding-field-engine-standard-template, roles-coach-accounts-tenant-isolation.

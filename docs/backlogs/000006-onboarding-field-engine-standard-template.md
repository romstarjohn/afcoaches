# Backlog: Onboarding: field engine and platform standard template

- **ID:** 000006
- **Slug:** onboarding-field-engine-standard-template
- **Status:** open
- **Created:** 2026-11-17

## Summary

Build the questionnaire engine (field types, validation, conditions, versioning) and the platform standard
template derived from market intake forms plus African nutrition fields.

## Reference

- docs/definition-of-done.md §2.4 (three-layer model, field types, standard template content), §5 #10 (health screening), #11
- Market intake forms: Coachway, Pabau, Paperform (contact, goals, screening, injuries, activity, lifestyle, nutrition, consent)

## Scope Hint

- Field types: short/long text, number with unit, single/multiple choice, yes/no, scale, date, image, section header
- Per field: FR/EN label + help text, required, validation, single-condition display
- Questionnaire + version model; platform standard template managed by admins
- Standard template content as listed in DoD §2.4, each standard field with a stable key for profile mapping
- Health screening: own questions (PAR-Q+ only if licence confirmed, see decision-health-screening)
- Out of scope: coach customisation, client filling (next items)

## Acceptance Hint

- Admin can create/publish a new standard template version without code changes
- Standard fields have stable keys and fixed types
- Unit tests for every field type validation and condition logic

## Notes

Depends on: project-foundation (can start in parallel with client-invitation-consent). Content of screening section depends on decision-health-screening.

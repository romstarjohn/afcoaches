# Backlog: Training plan builder and exercise library

- **ID:** 000012
- **Slug:** training-plan-builder
- **Status:** open
- **Created:** 2026-11-17

## Summary

Coaches create, copy and edit training plans (days -> exercises with sets/reps/rest/notes) from an exercise
library with FR/EN names.

## Reference

- docs/definition-of-done.md §2.1 (training plans)

## Scope Hint

- Exercise library (FR/EN, description, optional image/video link), coach-specific exercises
- Plan model (owner coach, type, visibility placeholder), PlanDay, PlanItem for exercises
- Create, copy, edit, archive plans; mobile-friendly editor
- Out of scope: assignment and visibility (see plan-visibility-assignment-feed)

## Acceptance Hint

- Coach builds a 4-week plan without help in a test session
- Tenant isolation tests for all plan endpoints

## Notes

Depends on: roles-coach-accounts-tenant-isolation.

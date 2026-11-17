# Backlog: Nutrition plan builder and coach recipes

- **ID:** 000013
- **Slug:** nutrition-plan-builder
- **Status:** open
- **Created:** 2026-11-17

## Summary

Coaches create nutrition plans (days -> meals -> dishes with portion) with automatic macros, and their own
private recipes from library ingredients.

## Reference

- docs/definition-of-done.md §2.1 (nutrition plans, own recipes), §2.5

## Scope Hint

- PlanItem for meals referencing dishes + portion; daily/plan totals of kcal and macros
- Coach recipes from library ingredients, visible only to that coach
- Use client requirements (allergies, restrictions) as warnings when building client plans

## Acceptance Hint

- Totals match calculation tests
- Coach recipes invisible to other coaches (tests)
- Allergy conflict warning shown

## Notes

Depends on: training-plan-builder (shared plan model), food-library-model-verification, client-requirements-profile.

# Backlog: Food library: data model, macro calculation and verification workflow

- **ID:** 000010
- **Slug:** food-library-model-verification
- **Status:** open
- **Created:** 2026-11-17

## Summary

The core differentiator: ingredients and African dishes with automatically calculated macros and a
verification workflow by a qualified nutrition professional.

## Reference

- docs/definition-of-done.md §2.5 (fields, verified flag, macro tests +-2 %, admin editing)
- Market analysis: competitors lack verified African data; recipe variance (e.g. jollof Lagos vs Accra) is the main error source

## Scope Hint

- Ingredient: names FR/EN/local, region/country, nutrients per 100 g, source, licence
- Dish: ingredients with grams, portions, computed kcal/protein/carbs/fat per portion
- Verification: verified_by, verified_at; unverified entries admin-only
- Admin UI (Django admin) to add/edit/verify without developers; CSV import command
- Out of scope: the actual content import (see food-library-content)

## Acceptance Hint

- Macro calculation unit-tested against reference values (+-2 %)
- Unverified dishes never visible to coaches (tests)

## Notes

Depends on: project-foundation. Can run in parallel to onboarding.

# Backlog: Plan visibility, assignment to clients and follower feed

- **ID:** 000014
- **Slug:** plan-visibility-assignment-feed
- **Status:** open
- **Created:** 2026-11-17

## Summary

Make plans reach people: public plans and coach posts in the follower feed (read-only), private plans
assigned to clients with start date.

## Reference

- docs/definition-of-done.md §2.1 (visibility, posts, assignment), §2.2 (feed, read-only), §2.3 (client sees private plans)

## Scope Hint

- Visibility public/private; assignment with start date; client notified
- Coach posts (text, image, optional plan link); feed for followers and clients
- Follower view: fully readable plans, no feedback UI, no prompts
- Image handling for posts (public content, separate from private client images)

## Acceptance Hint

- Followers see only public plans of followed coaches
- Server denies any follower feedback request (403, tests)
- Clients see assigned private plans

## Notes

Depends on: nutrition-plan-builder, coach-discovery-follow, client-invitation-consent.

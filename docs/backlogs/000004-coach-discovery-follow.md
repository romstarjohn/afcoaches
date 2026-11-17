# Backlog: Coach discovery, follow/unfollow and coaching request

- **ID:** 000004
- **Slug:** coach-discovery-follow
- **Status:** open
- **Created:** 2026-11-17

## Summary

Followers find coaches, follow them and can ask for coaching. This is the top of the freemium funnel
(follower -> client) the pilot must validate.

## Reference

- docs/definition-of-done.md §2.2 (discover, follow/unfollow, request coaching), §3 (>= 1 follower -> client conversion)

## Scope Hint

- Coach directory (list + profile page), follow/unfollow, "my coaches" list
- "Request coaching" contact request to a coach (no payment), coach sees and answers requests
- Follower has no feedback/check-in capability anywhere (server-side denial prepared)
- Follow, unfollow and "request coaching" require a verified email: add `IsEmailVerified`
  (apps/accounts/permissions.py, from 000002) to these endpoints; browsing the directory stays open
- Out of scope: feed content (see plan-visibility-feed)

## Acceptance Hint

- Follow/unfollow works and is reflected immediately
- Coaching request reaches only the addressed coach
- Tests prove followers cannot hit any client-only endpoint (403)
- Test: a member with an unverified email gets 403 on follow and coaching request, 200 after verification

## Notes

Depends on: roles-coach-accounts-tenant-isolation.

---
name: backlog
description: Manage backlog todo documents in docs/backlogs with deterministic tooling (tools/backlog.py). Use when creating backlog items with duplicate checks, especially deferred follow-ups discovered during in-progress task/RFC work that need recoverable context, or closing/archiving backlog items with explicit reasons.
---

# Backlog Workflow (coachsurmesure)

Adapted from jiangzhe/doradb `.agents/skills/backlog`; the Rust tools are replaced by
`tools/backlog.py` (Python 3, stdlib only). Run all commands from the project root.

Two prompt workflows:
1. `backlog create`: create a new backlog todo with duplicate check.
2. `backlog close`: close/archive an open backlog item with reason.

## `backlog create` Required Flow

1. Understand and confirm the user's backlog intention first.
2. Classify the item: **standalone follow-up** or **intentionally deferred work** from active task/RFC execution.
3. Collect required fields: title, slug (lowercase, hyphens), summary, reference, scope hint, acceptance hint; optional notes.
4. If deferred from active work, also require all four (the tool rejects a partial set):
   - `deferred from`: source task doc, RFC doc/phase, or both
   - `defer reason`: why postponed now
   - `findings`: what was learned and must not be lost
   - `direction hint`: what future planning should revisit, prefer or avoid
5. Duplicate check (open docs only):
```bash
tools/backlog.py find-duplicates --title "Backlog title" --slug "backlog-title"
```
6. If candidates are listed, show them and ask whether to continue.
7. Create with an allocated id:
```bash
tools/backlog.py create-doc \
  --title "Backlog title" --slug "backlog-title" \
  --summary "..." --reference "..." \
  --scope-hint "..." --acceptance-hint "..." \
  --auto-id
```
   For deferred work add `--deferred-from`, `--defer-reason`, `--findings`, `--direction-hint`.
8. If `docs/backlogs/next-id` is missing: `tools/backlog.py init-next-id`.
9. Report the created path.

For multiline text, markdown or backticks use the file flags (`--summary-file`, `--reference-file`,
`--scope-hint-file`, `--acceptance-hint-file`, `--notes-file`, `--deferred-from-file`,
`--defer-reason-file`, `--findings-file`, `--direction-hint-file`). Write the text with a quoted
heredoc (`<<'EOF'`) to a file in the scratchpad directory, then pass that path.

## `backlog close` Required Flow

1. Resolve and confirm the target is an open doc in `docs/backlogs/`. For id shorthand:
```bash
tools/backlog.py search-by-id --id 000123 --scope open
```
2. Require an explicit close type (`done`, `stale`, `duplicate`, `superseded`, `wontfix`) and detail.
3. Close:
```bash
tools/backlog.py close-doc --path docs/backlogs/000123-example.md --type stale --detail "Superseded by later design"
```
   (`--id 000123` works instead of `--path`; use `--detail-file` / `--reference-file` for longer text.)
4. Confirm the file moved to `docs/backlogs/closed/` and contains `## Close Reason`.

## Output Quality Bar

Every backlog doc must be:
1. Specific about why the follow-up exists now.
2. Linked to source task/RFC work when intentionally deferred.
3. Explicit about why it was deferred and what was learned.
4. Useful as future planning input, not just a reminder title.

## Storage

- Open: `docs/backlogs/<6digits>-<slug>.md` · Closed: `docs/backlogs/closed/`
- Template (reference only, ignored by tooling): `docs/backlogs/000000-template.md`
- Counter: `docs/backlogs/next-id` (never edit by hand; ids already on disk are skipped anyway)
- Tests: `.venv/bin/python -m unittest tests/test_backlog.py`

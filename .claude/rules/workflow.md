# Agent workflow rules — AEDIST

## Test one before blasting

Before any parallel batch of API calls: (1) dry-run to check prompt assembly, (2) run 1 real call per regime, (3) inspect output tokens, wall time, content quality, (4) then launch the full batch.

**Why:** Phase 1 burned ~$5 on 26 models before anyone noticed they were answering from memory. One test call catches it in 30 seconds.

## Audit before instrumenting

Before building new diagnostic infrastructure (schema changes, sweep options, new tables) for a suspected phenomenon, run a retrospective check on existing data to confirm the phenomenon is actually present. If the premise fails, close the ticket with a documented non-finding and no code.

**Why:** Ticket 0073 proposed schema changes + runner path + tex table to diagnose cold-start drift that a 5-minute check on measurements.jsonl did not support.

## Prefer skills over commands

New slash-invocable automation → `.claude/skills/<name>/SKILL.md`, never `.claude/commands/*.md` (legacy format). User-level skills go to `~/.claude/skills/` (IDH); project-level only for skills inseparable from this repo's harness (e.g. git-erg ticket-* skills). Skills must gracefully degrade when project-specific conventions are absent.

## Worktree paths

In an `EnterWorktree` session, `Edit`/`Write`/`Read` tools accept any absolute path. Edits at `/home/haduong/<repo>/<file>` go to the **main repo**, not the worktree. Always use worktree-rooted paths. Confirm with `pwd` and `git branch --show-current` before committing — if branch is `main`, stop.

## Closing issues and PRs

Never close GitHub issues or PRs without explicit user confirmation, even when acceptance criteria appear met. Recommend closures but always ask first, especially never close PRs belonging to other sessions or worktrees.

## Ruff post-edit hook strips unused imports

Always group import + usage in the **same Edit** call. Never add an import in one edit and its usage in another — ruff deletes the import between edits. When renaming a symbol: `replace_all` old→new FIRST, then add the new import line.

**Why:** The ruff hook runs after every Edit. Import-then-usage round-trips are the #1 cause of wasted edits in this repo.

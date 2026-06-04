---
name: ticket-new
description: Create a local %erg 0.1 file for agent coordination.
disable-model-invocation: false
user-invocable: true
argument-hint: [title]
---

# Create local ticket

**Input:** anything — a title, a sentence, a JSON blob from `gh`, a paste
from a conversation. Extract the intent and normalize to `%erg 0.1`.

## Steps

1. **Narrow the collision window** (optimistic concurrency — see Rules):
   ```bash
   git fetch origin
   git ls-tree origin/main tickets/ --name-only | tail -3
   ```
   If origin/main carries IDs your checkout lacks, allocate above them.

2. **Allocate atomically** with the committed binary (never compute IDs
   by hand):
   ```bash
   tickets/erg new "{imperative title}"
   ```
   This creates `tickets/{ID}-{slug}.erg` with the required preamble
   (Title, Created, Author), an empty log with a `created` entry, and an
   empty body. O_EXCL + retry handles same-checkout races.

3. Fill the body:
   ```
   ## Context
   {why this work exists}

   ## Actions
   1. {concrete step}

   ## Test
   {first test to write — TDD red step}

   ## Exit criteria
   {definition of done}
   ```

4. Validate and commit the ticket file (on a branch, never on main):
   ```bash
   tickets/erg validate tickets/{ID}-{slug}.erg
   git add tickets/{ID}-{slug}.erg && git commit
   ```

## Rules

- **IDs are allocated optimistically.** Parallel sessions can pick the
  same ID; that is accepted, not prevented. No reservation machinery
  (author decision 2026-06-04, git-erg#282 wontfix). The fetch in step 1
  narrows the window; `erg check` in CI detects what slips through.
- **Collision recovery: move to the next seat.** If `erg check` (or a
  merge/rebase, or a PR review) surfaces a duplicate ID: rename your
  file to the next free ID on the same branch, update any `Blocked-by:`
  or `Ticket-ref:` lines pointing at it, recommit. One commit, no
  redesign, no escalation. (Precedents: 0412→PR #701, 0418→0420
  commit 9e32373f, 0421→0425 on PR #710.)
- **No `Status:` header** in %erg 0.1 — open/closed is inferred from
  path (`tickets/` vs `tickets/closed/`) or a `Closed:` header.
- **Headers**: Title, Created, Author, Closed, Label, Blocked-by. Run
  `tickets/erg spec` for the format.
- **Blocked-by**: one line per dependency, 4-digit ticket IDs.
- **Log**: append-only, before `--- body ---`, never at EOF. Format:
  `{ISO-timestamp} {actor} {verb} [{detail}]`. Verbs: `created`,
  `note`, `claimed`, `closed`.

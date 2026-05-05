# Ticket format spec — %erg v1

## Overview

Local ticket system for agent coordination across worktrees on one machine.
Not a replacement for GitHub Issues — those handle inter-agent and human coordination.
Tickets are committed to git and travel with the repo.

## File format

Extension: `.erg`
Location: `tickets/` (active), `tickets/archive/` (closed, old)
Encoding: UTF-8, LF line endings.

### Magic first line

```
%erg v1
```

Every `.erg` file starts with this line. It declares the format version
and enables file-type detection without relying on the extension. A future
`%ticket v2` adds headers without breaking v1 validators (they reject
unknown versions rather than silently misparsing).

### Structure

```
%erg v1
Title: Short imperative description
Created: 2026-03-27
Author: claude

--- log ---
2026-03-27T10:00Z claude created

--- body ---
Free-form markdown body.
```

Three sections, in order:
1. **Headers** — RFC 822 style, one per line, immediately after magic line.
2. **Log** — append-only ledger, after `--- log ---` separator.
3. **Body** — free-form markdown, after `--- body ---` separator.

A blank line ends the header block. Both separators are required (the
validator rejects files missing either one).

### Headers (closed set, v1)

| Header | Required | Type | Values |
|--------|----------|------|--------|
| `Title` | yes | string | Short imperative sentence |
| `Closed` | no | string | Reason for closure (free text) |
| `Created` | yes | date | `YYYY-MM-DD` |
| `Author` | yes | string | Agent or human identifier |
| `Blocked-by` | no | ref | Ticket ID (repeatable) |

No other headers are valid in v1. No `X-` extensions.

**`Closed` header:** absent means open. Present (any value) means closed. Use
`erg close <id> <reason>` — it appends the header automatically. Do not write
it by hand except in migrations.

**`Blocked-by` references:**
- A 4-digit ID (e.g., `0041`) refers to a local ticket.
- Repeatable: one `Blocked-by:` line per dependency.
- A blocker must have a `Closed:` header to unblock.
- `gh#N` (GitHub issue refs) are deprecated and rejected by the validator.

### ID assignment

The ticket ID is derived from the filename, not a header.

Filename pattern: `{ID}-{slug}.erg`
- ID: zero-padded sequential number, 4 digits. `0001`, `0002`, ...
- Slug: lowercase kebab-case, ASCII only (`[a-z0-9-]`).

To assign the next ID: read filenames in `tickets/` and `tickets/archive/`,
extract the numeric prefix from each, take the maximum, increment by 1,
zero-pad to 4 digits. If no tickets exist, start at `0001`.

**Collision handling:** optimistic. Two worktrees may pick the same number.
The pre-commit validator catches duplicate IDs. The agent that loses renames
its ticket (increment again). This matches git's own optimistic concurrency.

### Log section

Append-only. Each line records one event:

```
{ISO-8601-timestamp} {actor} {verb} [{detail}]
```

**Timestamp:** `YYYY-MM-DDThh:mmZ` (UTC, minute precision).
**Actor:** agent or human identifier (e.g., `claude`, `user`).
**Verbs (closed set, v1):**

| Verb | Meaning |
|------|---------|
| `created` | Ticket created |
| `note` | Free-form annotation |

Lines are never edited or deleted. To correct an error, append a new line.

### Body section

Free-form markdown. Convention for actionable tickets:

```
## Context
Why this work exists.

## Actions
1. Concrete steps.

## Test
First test to write (TDD red step).

## Exit criteria
Definition of done.
```

Not enforced by the validator. Agents are encouraged to follow the convention
but the body is structurally unconstrained.

## Coordination is out of scope

%erg v1 describes what a ticket is, not how concurrent agents or worktrees
share access to one. There is no claim file, no lock, no doing-but-mine state.
If two agents need to avoid stepping on each other, they observe out-of-band
signals — typically a git branch whose name contains the ticket ID — and
coordinate there. Such conventions are workflow choices, not properties of
this format.

## Ready query

A ticket is **ready** when:
- No `Closed:` header present
- Every `Blocked-by` local ref points to a ticket that has a `Closed:` header

### Archive criteria

A ticket is **archivable** when:
- Has a `Closed:` header
- Last log entry older than 90 days
- Not referenced by any live ticket's `Blocked-by` header (DAG safety)

Archive moves the file to `tickets/archive/` via `git mv`.

## Validator rules (pre-commit)

The Go validator enforces:
1. Magic first line is `%erg v1` (reject unknown versions)
2. All required headers present
3. No unknown headers (`Status:` is no longer valid — use `Closed:`)
4. `Created` is a valid ISO date (`YYYY-MM-DD`)
5. Filename matches `NNNN-{slug}.erg` pattern (4-digit ID, ASCII slug)
6. No duplicate IDs across `tickets/` and `tickets/archive/`
7. `Blocked-by` local refs point to existing ticket IDs
8. No dependency cycles
9. Log lines match `{timestamp} {actor} {verb}` format
10. Each separator (`--- log ---`, `--- body ---`) appears exactly once
11. `gh#N` refs in `Blocked-by` are rejected (deprecated scheme)

## Relationship to GitHub Issues

| Concern | Tool |
|---------|------|
| Local work organization | `.erg` files |
| Multi-agent coordination | GitHub Issues |
| Public visibility, review | GitHub Issues + PRs |

A ticket may reference a GitHub issue (`Blocked-by: gh#435`) but never
caches it. The two systems are independent.

## Postel's Law

**Strict on write, tolerant on read.** The validator enforces `%erg v1`
on commit. But you — the agent — are the parser for arbitrary input. If you
receive ticket-like information in any form (raw JSON from `gh`, a sentence,
a markdown sketch), understand the intent and write clean `%erg v1`. The
pre-commit hook catches mistakes. The tolerance is in you, not the tooling.

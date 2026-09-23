# AI Agent Guidelines

> `CLAUDE.md` contains only `@AGENTS.md` — do not modify it (enforced by pre-commit hook).

The generic workflow (phases, worktrees, delegation, escalation, git discipline)
lives in the harness rules under `~/.claude/rules/`, loaded into every session,
and skills are listed in each session's skill catalog. This file holds only what
is specific to this repo. Do not copy harness content back here: the copy drifts.
The skills table this file used to carry named four skills that no longer
existed, and agents routed to their nearest living neighbour.

## Configuration

| Location | Purpose |
|----------|---------|
| `tickets/` | Local `.erg` tickets (instructions: `tickets/AGENTS.md`) |
| `tickets/erg` | Tickets management binary. |
| `.claude/rules/` | Project rules (TODO: replace with scoped hooks) |
| `.claude/settings.json` | Project permissions and hooks |

## Imagine

Beyond the harness advisor stance: turn codesmell metrics into design
architecture improvements.

## Tickets

A ticket ready to execute carries the first test in its body, states the
definition of done literally, and hands off the context an executor needs.

## Execute

Use `make check-fast` during development, `make check` before the merge request.
Maintain the Makefile DAG: prerequisites and targets must match each script's
actual file reads and writes. Doc propagation belongs to the merge request.

## Verify in proportion to what can break

Before merging, decide which checks the change needs and state them on the PR:

- **Tickets only**: `tickets/erg check tickets/`.
- **Docs, config, STATE**: `make lint`, and a read of the loaded or rendered result.
- **Prose**: rebuild the document; `/review-pr-prose` for report text.
- **Code, experiments**: tests for the changed behaviour, and `make check`.

Anything beyond tickets gets at least one independent reviewer on a model other
than the coder's (`/review` or `/review-pr`, scoped to the risk). Fix all
issues, nits included; push back against "no need to fix now", and open a
ticket only for oversized deferred work. Consider `/simplify` and codesmell
checks for code. Up to three review/fix cycles, then escalate. Before merging,
`/verify-gate` checks every exit criterion against concrete evidence (commit SHA
+ file:line, or a test id).

## Chore tooling

For one-shot chore PRs (tickets/, docs/, .claude/, top-level docs, .github/workflows/, *.md) use `scripts/quickpr.sh "<message>" <files...>` — one command branches off main, commits, pushes, opens a PR with auto-merge, and restores the starting branch. Refuses src/, tests/, experiments/ so implementation work still goes through `/hunt` → `/roar`.

## Autonomous mode

In autonomous mode (`/raid`), the orchestrator never defers for human input. In
the face of hard issues, it resorts first to a diverse team of agent experts. It
then escalates to deep research. Thirdly, it works around the issue.

# AI Agent Guidelines

> No `CLAUDE.md` here: Claude Code (2.1.277+) loads this file natively, plus the parent `~/CNRS/AGENTS.md`. Do not add a `CLAUDE.md` or `.claude/CLAUDE.md`; either one disables that fallback.

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
| `memory/` | Project memory: index, topics, journal (v8) |

## Project memory

Read [memory/MEMORY.md](memory/MEMORY.md) at task start when it exists. Open
the topics that match the task; search topics and the journal with `rg` when
the task or an obstacle calls for recall, and again when the task changes
materially. Missing memory does not block work; report a known incomplete
installation.

This repository is public. At roar, commit significant facts here only when
fit for a public reader; private material may enter only as age-encrypted
`.age` ciphertext, and until this repository pins such a mechanism it stays
out. Journal entries are append-only; corrections link back from new
entries. Consolidation follows the harness smelt skill. `memory/MEMORY.md`
is at most 100 lines including headings and blank lines. No timer, TTL or
automatic rule proposal. Sources and dispositions:
[memory/SOURCES.md](memory/SOURCES.md).

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
- **Prose**: rebuild the document; `/gaze` (prose mode) for report text.
- **Code, experiments**: tests for the changed behaviour, and `make check`.

Anything beyond tickets gets at least one independent reviewer on a model other
than the coder's (`/review` or `/gaze`, scoped to the risk; `/verify-gate` gates the merge). Fix all
issues, nits included; push back against "no need to fix now", and open a
ticket only for oversized deferred work. Consider `/simplify` and codesmell
checks for code. Up to three review/fix cycles, then escalate. Before merging,
`/verify-gate` checks every exit criterion against concrete evidence (commit SHA
+ file:line, or a test id).

## Chore tooling

For one-shot chore PRs (tickets/, docs/, .claude/, top-level docs, .github/workflows/, *.md) use `scripts/quickpr.sh "<message>" <files...>` — one command branches off main, commits, pushes, opens a PR with auto-merge, and restores the starting branch. Refuses src/, tests/, experiments/ so implementation work still goes through `/hunt` → `/roar`.

## Autonomous mode

In autonomous mode (`/raid`), the orchestrator does not stop for *how*
questions: in the face of hard issues it resorts first to a diverse team of
agent experts, then to deep research, then works around the issue. Questions of
*what* follow the harness: a change of intent (exit criteria dropped, reworded
or added; an expired premise) goes back to the author, as `/raid` and the
harness escalation ladder require.

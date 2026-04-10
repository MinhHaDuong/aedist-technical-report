# AI Agent Guidelines

> `CLAUDE.md` contains only `@AGENTS.md` — do not modify it (enforced by pre-commit hook).

## Configuration

| Location | Purpose |
|----------|---------|
| `hooks/` | Git hooks (pre-commit, pre-push, post-checkout) |
| `tickets/` | Local `.erg` tickets (committed, travel with repo) |
| `tickets/tools/go/` | Validator source; build with `go build -o erg .` |
| `.claude/rules/` | Project rules (incl. `tickets.md` from git-erg) |
| `.claude/skills/` | Project skills (ticket-* from git-erg) |
| `.claude/hooks/` | Project-specific hooks |
| `.claude/settings.json` | Project permissions and hooks |

## Imperial Dragon workflow

Every task passes through five phases.
Maintain awareness of the conversation's current phase to behave accordingly.
Infer the initial phase and announce it (e.g., `[→ Imagine]`) at conversation start, then announce transitions inline: `[Phase → Phase] reason`.

### Imagine
Engage with the user to form a vision.

Context: Worktree isolation, `imagine-` branch.

Deliverable: No production code commit, change only the conversation state and possibly tickets.

Agent posture: Act as my high-level advisor. Challenge my thinking, question my assumptions, and expose blind spots. Stop defaulting to agreement. If my reasoning is weak, break it down and show me why.

Conversation guidelines: Imagine specs. Gather information. Brainstorm freely. Ask questions. Surface motivations. Explore what success looks like. Generate portfolio of options with their probabilities. Go beyond conventional habits to explore new approaches. Take the high road. Transform codesmell metrics into design architecture improvements.

### Plan

Scope: Focus on one issue. Scope-creep guard: Create new tickets if investigation reveals sub-issues. Divide-and-conquer complexity: Transform a hard ticket into a tracking ticket and create sub-tickets. Use `Blocked-by:` to sequence work.

Deliverable: a ticket ready to execute. No production code commit, change only ticket(s). The ticket includes the first test in the ticket body, specifies the definition of done literally, provides guidance and hands-off helpful context.

Explore alternatives, design strategies, and prototype approaches using throwaway code, worktree isolated.

Consider interaction with other tickets and PR.

### Execute

Goal: deliver a PR to close one ticket.

Environment: fresh context in a worktree, the ticket is the only input. Worktree mandatory: never touch files on main.

Method: Autonomous execution using test-driven development. Use `make check-fast` during development, `make check` before PR.

Constraint: Maintain the Makefile DAG, prerequisites and targets must match each script's actual file reads and writes. Doc propagation belongs to the PR.

### Verify

Review each PR before merging:

1. **Review**: Route between `/review` (stock), `/review-pr` or `/review-pr-prose` (IDH).
2. **Fix**: Fix all issues. Nits: fix them. Push back against "No need to fix now" mindset. Non-fixed open tickets for oversized deferred work.
3. **Lint**: Consider `/simplify`, advanced linter and codesmells checks.
4. **Iterate**: Up to three review/fix cycles.

### Celebrate

Cleanup worktrees and branches, summarize what was accomplished, reflect on lessons, consolidate memory, dream forward.

## Skills (slash commands)

### [git-erg](https://github.com/MinhHaDuong/git-erg) (travels with repo — always available)

| Skill | When | Purpose |
|-------|------|---------|
| `/ticket-new [title]` | Creating a local ticket | Write `%erg v1` file with next ID, commit |
| `/ticket-ready` | Choosing what to work on | List unblocked, unclaimed tickets |
| `/ticket-claim NNNN` | Starting work on a ticket | Write `.wip` claim, set `Status: doing`, commit |
| `/ticket-close NNNN` | Completing work | Set `Status: closed`, release `.wip`, commit |
| `/ticket-release NNNN` | Abandoning work | Restore `Status: open`, release `.wip`, commit |

### [Imperial Dragon Harness](https://github.com/MinhHaDuong/ImperialDragonHarness) (user-level — may not be available)

| Skill | When | Purpose |
|-------|------|---------|
| `/start-ticket N` | Starting work on a GitHub issue | Create worktree, write first test, transition to Execute |
| `/celebrate` | After completing a ticket | Reflect, update STATE, clean up |
| `/end-session` | User ends a work session | Push branches, run tests, refresh STATE |
| `/new-ticket` | Creating a GitHub issue | Write handoff document with test spec |
| `/review-pr N` | Reviewing a pull request (code) | Multi-perspective agent review |
| `/review-pr-prose N` | Reviewing a pull request (prose) | Simulated peer review panel |
| `/memory` | Writing or sweeping persistent memory | Enforce caps, TTLs, staleness |
| `/autonomous` | Unsupervised autonomous session | Imperial Dragon cycles with 60/40 balance |
| `/submission-branch` | Creating a submission branch | Sprout, freeze, revision lifecycle |
| `/submission-readiness` | Pre-submission gate | Checklist before sprouting |
| `/update-publist` | Adding/updating a publication | Edit Ha-Duong.bib, deposit on HAL via SWORD |

## Autonomous workflow (details in /orchestrator skill)

Orchestrator reviews the tickets DAG and organize work in waves. It assembles teams of agents (isolation:worktree) working in imperial dragon order. It provisions the agents with context and brief, and supervises their work to break hangs or loops.
Team Imagine: each ticket gets reviewed and challenged. Why now, why this scope, should we do something else better...
Team Planning.
Team Verification: independently review the plans and annotate for prerequisites, assumptions, feasibility in environment.
Team Execute delivers the PR.
Team Verify fixes them.
Team Audit assumes non-compliance and lint, reverify, inspect scope creep and fix again.
The orchestrator receives the clean PRs, reviews each against its ticket, and performs the merge in order. It then loops to the first step.

In autonomous mode, orchestrator never defers for human input. In the face of hard issues, it resorts first to a diverse team of agent experts. It then escalates to deep research. Thirdly, it works around the issue.

## Two ticket systems

| Concern | Tool | Skills |
|---------|------|--------|
| Local work organization, sequencing | `.erg` files in `tickets/` | git-erg: `/ticket-new`, `/ticket-ready`, `/ticket-claim`, `/ticket-close` |
| Cross-worktree deconfliction | `.git/ticket-wip/*.wip` | git-erg: automatic via `/ticket-claim` and `/ticket-close` |
| Cross-agent coordination, public visibility | GitHub Issues | IDH: `/new-ticket`, `/start-ticket` |
| Linking the two | `Blocked-by: gh#N` in `.erg` headers | — |

Local tickets travel with the repo. GitHub issues are for humans and other agents. Use both; they don't overlap.

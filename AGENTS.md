# AI Agent Guidelines

> `CLAUDE.md` contains only `@AGENTS.md` — do not modify it (enforced by pre-commit hook).

## Configuration

| Location | Purpose |
|----------|---------|
| `tickets/` | Local `.erg` tickets (instructions: `tickets/AGENTS.md`) |
| `tickets/erg` | Tickets management binary. |
| `.claude/rules/` | Project rules (TODO: replace with scoped hooks) |
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

Consider interaction with other tickets and merge requests.

### Execute

Goal: deliver a merge request to close one ticket.

Environment: fresh context in a worktree, the ticket is the only input. Worktree mandatory: never touch files on main.

Method: Autonomous execution using test-driven development. Use `make check-fast` during development, `make check` before merge request.

Constraint: Maintain the Makefile DAG, prerequisites and targets must match each script's actual file reads and writes. Doc propagation belongs to the merge request.

### Verify

Review each merge request before merging:

1. **Review**: Route between `/review` (stock), `/review-pr` or `/review-pr-prose` (IDH).
2. **Fix**: Fix all issues. Nits: fix them. Push back against "No need to fix now" mindset. Non-fixed open tickets for oversized deferred work.
3. **Lint**: Consider `/simplify`, advanced linter and codesmells checks.
4. **Iterate**: Up to three review/fix cycles.

### Celebrate

Cleanup worktrees and branches, summarize what was accomplished, reflect on lessons, consolidate memory, dream forward.

## Skills

### [Imperial Dragon Harness](https://github.com/MinhHaDuong/ImperialDragonHarness)

| Skill | When | Purpose |
|-------|------|---------|
| `/start-ticket N` | Starting work on a GitHub issue | Create worktree, write first test, transition to Execute |
| `/celebrate` | After completing a ticket | Reflect, update STATE, clean up |
| `/end-session` | User ends a work session | Push branches, run tests, refresh STATE |
| `/new-ticket` | Creating a GitHub issue | Write handoff document with test spec |
| `/review-pr N` | Reviewing a merge request (code) | Multi-perspective agent review |
| `/review-pr-prose N` | Reviewing a merge request (prose) | Simulated peer review panel |
| `/memory` | Writing or sweeping persistent memory | Enforce caps, TTLs, staleness |
| `/autonomous` | Unsupervised autonomous session | Imperial Dragon cycles with 60/40 balance |
| `/submission-branch` | Creating a submission branch | Sprout, freeze, revision lifecycle |
| `/submission-readiness` | Pre-submission gate | Checklist before sprouting |
| `/update-publist` | Adding/updating a publication | Edit Ha-Duong.bib, deposit on HAL via SWORD |

### Chore tooling

For one-shot chore PRs (tickets/, docs/, .claude/, top-level docs, .github/workflows/, *.md) use `scripts/quickpr.sh "<message>" <files...>` — one command branches off main, commits, pushes, opens a PR with auto-merge, and restores the starting branch. Refuses src/, tests/, experiments/ so implementation work still goes through `/start-ticket` → `/celebrate`.

## Autonomous workflow (details in /orchestrator skill)

Orchestrator runs tickets in waves with isolated worktrees and one ordered loop:
1. Imagine: challenge ticket scope, motivation, and alternatives.
2. Plan + Verify: produce plans, then independently check assumptions and feasibility.
3. Execute + Verify: deliver a merge request, then fix all review findings.
4. Audit: re-check for non-compliance, lint gaps, and scope creep.
5. Gate + merge: approve only clean merge requests, merge in dependency order, then repeat.

In autonomous mode, orchestrator never defers for human input. In the face of hard issues, it resorts first to a diverse team of agent experts. It then escalates to deep research. Thirdly, it works around the issue.

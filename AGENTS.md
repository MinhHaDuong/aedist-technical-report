# AI Agent Guidelines

> `CLAUDE.md` contains only `@AGENTS.md` — do not modify it (enforced by pre-commit hook).
> Imperial Dragon Harness: <https://github.com/MinhHaDuong/ImperialDragonHarness>

## Configuration

| Location | Purpose |
|----------|---------|
| `~/.claude/rules/` | Generic rules (git, workflow, coding, state-roadmap) |
| `~/.claude/skills/` | Generic skills (celebrate, review-pr, memory, etc.) |
| `~/.claude/hooks/` | Generic hooks (on-start identity setup) |
| `.claude/rules/` | Project-specific rules (incl. `tickets.md` spec) |
| `.claude/skills/` | Project-specific skills (incl. `ticket-*` skills) |
| `.claude/hooks/` | Project-specific hooks |
| `.claude/settings.json` | Project permissions and hooks |
| `hooks/` | Git hooks (pre-commit, pre-push, post-checkout) |
| `tickets/` | Local `.erg` tickets (committed, travel with repo) |
| `tickets/tools/go/` | Validator source; build with `go build -o erg .` |

## Imperial Dragon workflow

Every task passes through five phases (five claws). Announce transitions inline: `[Phase → Phase] reason`.

### Imagine
Interactive discussion with the user on an `explore-{topic}` branch. Imagine specs, gather information, brainstorm freely. Ask questions, surface motivations, explore what success looks like.
Generate portfolio of options with their probabilities. Go beyond conventional habits to explore new approaches. Take the high road.
Act as my high-level advisor. Challenge my thinking, question my assumptions, and expose blind spots. Stop defaulting to agreement. If my reasoning is weak, break it down and show me why.

Commits are workspace artifacts unless the conversation produces a small fix. Deliverable: a shared vision, plus one of:

- **Tickets** — non-trivial work gets one local ticket per action item (`/ticket-new`). Use `Blocked-by:` headers to encode the dependency graph. For cross-agent or public-facing coordination, also open a GitHub issue (`/new-ticket`).
- **Small fix** — if it fits in one red/green/refactor cycle, do it on the explore branch. TDD still applies.
- **Nothing actionable** — delete the branch at session end.

### Plan
Explore alternatives, design strategies, prototype approaches. Use local `.erg` tickets as the planning artifact — write tickets with full context (`/ticket-new`). **Specify the first test in the ticket body** — the Execute phase enforces TDD. Use `Blocked-by:` to sequence work. Review tickets for intent over metrics. No production commits yet. Deliverable: a ticket with test spec.

For public-facing or cross-agent work, also open a GitHub Issue (`/new-ticket`) and link via `Blocked-by: gh#N`.

### Execute
Runs in a fresh context — the ticket is the only input.

- **Local tickets**: `/ticket-claim NNNN` to claim, then execute.
- **GitHub issues**: `/start-ticket N` as before.

Claiming writes a `.wip` file (cross-worktree safe) and sets `Status: doing`.

Autonomous execution using test-driven development. The inner cycle is:

1. **Red**: write a failing test that defines the expected behavior. Commit.
2. **Green**: write the minimum code to make it pass. Commit.
3. **Refactor**: clean up, then confirm tests still pass. Use `make check-fast` during development. Commit.
4. **PR**: Pass `make check` gate, then push and open a PR.
5. **Close**: `/ticket-close NNNN` to mark done and release the claim.

Use `make check-fast` during development, `make check` before opening a PR. Makefile truth: prerequisites and targets must match each script's actual file reads and writes.

### Verify
Review each PR before merging:

1. **Review**: `/review-pr` or `/review-pr-prose`.
2. **Fix**: Fix all issues. Nits: fix them. Code smells: ultrathink architectural improvements.
3. **Iterate**: Up to three review/fix cycles.

### Celebrate (autonomous)
Runs via `/celebrate`. Celebrating is not a formality — it closes the energy cycle. Reflect on what was accomplished and learned, consolidate memory, dream forward.

### Phase state

The agent must always know and declare its current phase.

- **At conversation start**: workflow rule infers the initial phase and announces it (e.g., `[→ Imagine]`).
- **At each transition**: announce explicitly with `[Phase → Phase] reason`.
- **No implicit transitions**: if no announcement was made, the phase hasn't changed.

## Skills (slash commands)

### Local tickets (`.erg`)

| Skill | When | Purpose |
|-------|------|---------|
| `/ticket-new [title]` | Creating a local ticket | Write `%erg v1` file with next ID, commit |
| `/ticket-ready` | Choosing what to work on | List unblocked, unclaimed tickets |
| `/ticket-claim NNNN` | Starting work on a ticket | Write `.wip` claim, set `Status: doing`, commit |
| `/ticket-close NNNN` | Completing work | Set `Status: closed`, release `.wip`, commit |
| `/ticket-release NNNN` | Abandoning work | Restore `Status: open`, release `.wip`, commit |

### GitHub and workflow

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

## Autonomous workflow

When exploration leads to multiple action items, create one `.erg` ticket per action item (`/ticket-new`). Use `Blocked-by:` to encode the dependency graph. Then work in waves, learning from each.

### Wave cycle

1. **Select** — `/ticket-ready` to list ripe tickets (unblocked, unclaimed).
2. **Launch** — `/ticket-claim NNNN` for each, in its own worktree. Independent tickets in parallel.
3. **Verify** — review each PR in a fresh-context worktree (`/review-pr`).
4. **Learn** — for each result:
   - **Success**: `/ticket-close NNNN`, `/celebrate`, save what worked as feedback memory.
   - **Failure**: diagnose root cause, `/ticket-release NNNN`, save lesson, re-ticket with diagnosis.
5. **Adapt** — read feedback memories before planning the next wave.
6. **Clean up** — worktrees, branches, stale PRs. Then start the next wave.

## Conversation scope

**Imagine conversations**: may produce zero or many tickets, or inline small fixes. The explore branch is the workspace; the `.erg` tickets (or PR) are the deliverables.

**Execute conversations**: one ticket per conversation. `/ticket-claim NNNN` at start, `/ticket-close NNNN` at end. Transition to Celebrate when the PR is merged and ticket closed. If investigation reveals sub-issues, `/ticket-new` for each — don't scope-creep.

## Two ticket systems

| Concern | Tool | Commands |
|---------|------|----------|
| Local work organization, sequencing | `.erg` files in `tickets/` | `/ticket-new`, `/ticket-ready`, `/ticket-claim`, `/ticket-close` |
| Cross-worktree deconfliction | `.git/ticket-wip/*.wip` | Automatic via `/ticket-claim` and `/ticket-close` |
| Cross-agent coordination, public visibility | GitHub Issues | `/new-ticket`, `/start-ticket` |
| Linking the two | `Blocked-by: gh#N` in `.erg` headers | Reference GitHub issues from local tickets |

Local tickets are committed to git and travel with the repo. GitHub issues are for humans and other agents. Use both; they don't overlap.

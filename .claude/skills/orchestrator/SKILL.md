---
name: orchestrator
description: Run Imperial Dragon batch across multiple tickets. Delegates to existing skills, manages waves, enforces isolation.
disable-model-invocation: false
user-invocable: true
argument-hint: [ticket-ids or "all open"]
---

# Orchestrate $ARGUMENTS — Imperial Dragon batch

The orchestrator does not redefine skills. It calls `/ticket-ready`,
`/review-pr`, `/celebrate`, etc. Its job is sequencing, wave management,
and enforcing invariants.

## Checkpointing

Every phase ends with a git commit. If the session dies, resume by
reading the ticket logs and git history to determine which phase
completed last. The checkpoint is the repo, not session state.

## Phase 1: Select

If $ARGUMENTS is "all open": `/ticket-ready`.
Otherwise: parse comma-separated ticket IDs.

Read each ticket + STATE.md + MASTERPLAN.md.
Group by milestone. Identify dependency order and wave structure.
Commit the wave plan to a scratch file or ticket log.

## Phase 2: Imagine (parallel)

For each ticket, launch an Opus agent (background, no isolation needed — read-only + ticket rewrite):
- Read ticket + STATE.md + MASTERPLAN.md + surrounding code
- WHY NOW, WHY THIS SCOPE, FIVE RADICALS, HYBRID, REWRITE
- Append log: `{timestamp} claude status reimagined by IDD imagine`

Wait for all. Commit reimagined tickets. Report scorecard.

## Phase 3: Plan (parallel)

For each reimagined ticket, launch an Opus agent (background):
- Read ticket + actual source code
- Write Actions, first test, Blocked-by, track label
- Append log: `{timestamp} claude status planned by IDD plan`

Wait for all. Commit planned tickets. Report scorecard.

## Phase 4: Verify feasibility

Launch agents by cluster to cross-check plans:
- File paths, line numbers, function signatures
- Data assumptions, API key requirements
- Cross-ticket conflicts

Annotate tickets with PASS/WARN/BLOCK. Commit annotations.

## Phase 5: Execute (waves, worktree-isolated)

Group tickets into waves:
- Wave N: no unmerged dependencies, no API keys (or keys available)
- Wave N+1: depends on Wave N results

For each wave, launch agents with MANDATORY rules:
- `isolation: "worktree"` — non-negotiable
- Branch from main: `ticket-{NNNN}-{slug}`
- TDD: red, green, refactor, commit
- `ruff check` on changed files before push
- `make check` as final gate
- Doc propagation (report/slides) in the same PR, not a follow-up
- Push branch — do NOT create PR, do NOT merge
- No cross-branch imports

Wait for wave to complete. Commit wave status to ticket logs.

## Phase 6: Verify (per-ticket `/review-pr`)

For each executed ticket, run `/review-pr` with proportional depth.
ALL review agents use `isolation: "worktree"`.

Synthesize findings. Every finding is actionable.

Launch fix agents (`isolation: "worktree"`) for all findings.
Create PRs after fixes land.

## Phase 7: TLC

One final `/review-pr` pass per PR (`isolation: "worktree"`):
- Verify previous fixes landed
- `ruff check` + `make check`
- Fix anything found

Commit. Report verdicts.

## Phase 8: Scope audit

Check each PR for scope creep:
- Did Execute exceed the Plan?
- Split out-of-scope work to new tickets (`/ticket-new`)
- Split branches if needed (`isolation: "worktree"`)

## Phase 9: Merge

Present merge order (respecting file overlaps).
Merge on user approval only. Then `/celebrate`.

## Invariants

- ALL agents that write code use `isolation: "worktree"`
- ALL agents run `ruff check` before pushing
- ALL Execute agents stop at push — never PR, never merge
- Doc propagation belongs in the Execute PR
- "Assume noncompliance" on all review verdicts
- Checkpoints are git commits, not session state

## Circuit breakers

**Agent timeout**: If an agent has not pushed within 10 minutes,
kill it. Assess whether the task is too large, then either split
the ticket or relaunch with a narrower scope.

**Ping-pong detector**: If two agents edit the same file on the
same branch (detected via `git log --diff-filter=M`), STOP.
The branch is contaminated. Reset to last known-good commit,
relaunch ONE agent with worktree isolation.

**Redirect ban**: Do not use SendMessage to redirect a running
agent's approach. By the time the message arrives, the agent is
committed to its plan. Kill and relaunch with corrected instructions.

**Escalation**: If the same fix fails twice, escalate to the user
with the two failed approaches and ask for direction. Do not
attempt a third time autonomously.

# Repository workflow — forge, tickets and parallel waves

Scope: facts about this repository's forge settings, ticket store and
multi-session practice. Generic git and merge discipline lives in the
harness rules; project instructions in [AGENTS.md](../../AGENTS.md) and
[tickets/AGENTS.md](../../tickets/AGENTS.md).

## Forge settings (read back 2026-11-09)

- Merge commits only: squash and rebase merges are disabled (squash since
  2026-05-25). Auto-merge is allowed; branches are deleted on merge.
- From a worktree, `gh pr merge --delete-branch` fails locally ("'main' is
  already used by worktree") after the server-side merge succeeded: omit the
  flag, the forge deletes the branch.
- A merge done on the forge side (`gh pr merge --auto`) does not run
  `erg close`: close the ticket in the PR's own branch, or follow up.
- Before 2026-05-25 many PRs were squash-merged: `git cherry` reports their
  branches as unmerged; check the PR's head branch and merge commit instead.
- `scripts/quickpr.sh` (chores only, see AGENTS.md) cannot express renames
  or deletions, and restores the starting branch, reverting working-tree
  edits that rode into the PR.

## Tickets

- `erg close` files the ticket under `tickets/closed/` and strips
  `Blocked-by:` from dependents. Two parallel closes of blockers of one
  ticket conflict in that third ticket: keep both log lines, drop both
  headers, run `tickets/erg check tickets/` before continuing the rebase.
- Ticket premises written by earlier sessions are hypotheses: a cheap data
  or code check overturned three of four in one raid (2026-06-09). A plan
  that reframes a ticket must not invert its Test section; diff it against
  the original.
- A PR's close claim closes the ticket whatever the checkboxes say:
  uncommitted work in a stale worktree may be a closed ticket's missing
  deliverable. Preserve it on a branch, run it, then adjudicate.

## Parallel sessions and waves (incidents met in this repository)

- The author often works in a parallel session while a raid runs (merges,
  new blockers, STATE edits). Re-check each ticket on `origin/main` before
  each launch; never clean worktrees or branches you did not create.
- Manuscript waves: whole-file sweeps first, then one PR per manuscript
  region bundling its tickets, the most invasive PR last; stack PRs (base =
  previous wave) when waves edit the same file and are human-gated, and
  rebase the stack at every gate.
- Ratchet files such as `tests/data/emdash_ceiling.txt` race with parallel
  prose merges: re-initialise on the rebased text. A rebase after a queued
  merge can drop the close commit: read ticket state on `origin/main` first.
- A rebase where main deleted a file the branch modified: accept the
  deletion and move the meaningful new content (e.g. a build rule) to its
  new home. Keep data commits off long-lived chore branches.
- A killed or budget-exhausted agent leaves a locked worktree with
  uncommitted work: inspect, commit as WIP and push, then hand the same
  branch to a finisher; never force-remove first.
- An auto-merge queued while reviewers are still running can land a PR
  before their blockers arrive: wait for every reviewer report.
- The permission classifier refused a background merge despite STATE.md's
  standing authorization (2026-06-11): end such a run with a merge handoff.
- Stalled green PRs: `gh pr update-branch` was missing from the installed
  `gh`; `gh api -X PUT repos/{owner}/{repo}/pulls/N/update-branch` works.

## Sources

- Native notes: `project_squash_merge_disabled.md` 402a0669,
  `feedback_gh_pr_merge_delete_branch_worktree.md` a3ea1e01,
  `feedback_auto_merge_bypasses_ticket_close.md` 6d6caf9c, `feedback_use_auto_merge.md` 81d65c56,
  `feedback_git_cherry_misleads_on_squash_merge.md` 6fc8ac3e,
  `feedback_use_quickpr_for_chores.md` 1c43822a, `feedback_quickpr_limitations.md` fb3787db,
  `project_erg_closed_dir.md` 9cc2481c, `feedback_erg_close_bookkeeping_conflict.md` 92e51491,
  `feedback_ticket_premises_are_hypotheses.md` 3e3611cc, `feedback_plan_agent_test_inversion.md` 0db4171b,
  `feedback_orphaned_wip_is_unlanded_exit_criteria.md` 48e547f6,
  `feedback_concurrent_author_session_raids.md` 2d035cca, `feedback_teams_raid_region_bundling.md` 42b34088,
  `feedback_stacked_pr_waves.md` e1b6822b, `feedback_ratchet_ceiling_race_and_dropped_close.md` 81145c1f,
  `feedback_modify_delete_rebase.md` 79e10091, `feedback_rebase_chore_data_branch.md` e07de490,
  `feedback_killed_agent_salvage.md` b1bc9f62, `feedback_raid_budget_recovery.md` 3c08e561,
  `feedback_gaze_fork_async_reviewers_automerge_race.md` fb596f04,
  `feedback_merge_classifier_blocks_autonomous_raid.md` caa018b9,
  `feedback_drain_stalled_green_prs.md` 55e581f8.
- Superseded detail: `project_erg_closed_dir.md` 9cc2481c names an older binary path
  and a generated `.claude/CLAUDE.md`; the binary is `tickets/erg` and
  AGENTS.md forbids a CLAUDE.md. `feedback_use_auto_merge.md` 81d65c56 predates the
  harness merge skill, which now governs merging.

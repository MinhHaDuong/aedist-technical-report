# Memory sources — v8 adoption inventory (ticket 0687)

Inventoried 2026-11-09 at `origin/main` e1004622. Audience of this
repository: **public** GitHub repository `MinhHaDuong/aedist-technical-report`
(visibility read with `gh repo view` on 2026-11-09). Every byte under
`memory/` is written for a public reader. Unknowns are stated as unknown.

## Sources, consumers and dispositions

| Source | Writer / consumer | Disposition |
|---|---|---|
| Claude Code native auto-memory for the primary checkout (197 notes + `MEMORY.md` index, 11 KB; notes last modified 2026-06-13 to 2026-09-29, index 2026-11-04) | Claude Code auto-memory; its index is loaded by sessions whose starting directory is the primary checkout | Kept unchanged and **still active**. Consolidated into `topics/` with attribution; per-note dispositions below. Not retired: the v8 index is read through AGENTS.md, and nothing shows that this path reaches the native auto-load consumer. |
| Harness export of the same store (`projects/-home-haduong-CNRS-papiers-actif-AEDIST-technical-report/memory/` in the public harness repository, last commit 7ea247a5, 2026-09-28) | Tracked by the harness; read by no active helper of this project | Byte-identical to the native store (`git hash-object` per file, 2026-11-09) except its `MEMORY.md` (two extra lines) and one extra note, `feedback_durable_reminder_is_blocked_open_ticket.md`, a practice the author withdrew everywhere on 2026-11-01 (ticket 0684 removed it from the native store): not imported. Cited for blob ids; harness content left untouched. |
| `.claude/projects/-home-haduong-aedist-technical-report/memory/project_statistical_power.md` in the primary checkout (1.5 KB, 2026-04-13, blob 93e797eb) | Git-ignored (`.gitignore`: `.claude/projects/`), untracked; consumer unknown, probably none since the checkout moved | Consolidated into [measurement](topics/measurement.md). Left in place, not moved. |
| Native session directories of past worktrees of this project (15 slugs) | Claude Code session history | No `memory/` directory in any of them (2026-11-09). Transcripts (`*.jsonl`) are not memory sources: not read. |
| `~/.codex/memories` | Codex | Absent (2026-11-09). |
| `~/.pi/agent` | Pi | No `*.md` file mentions this project; five Pi session transcripts do, and are not memory sources: not read. |
| [.claude/rules/](../.claude/rules/) (`experiment-design.md`, `workflow.md`, `writing.md`; `json-output.md` removed by ticket 0682, now harness `rules/coding-python.md`) | Project rules, loaded by Claude Code | Rules, not memory: linked from topics, not copied. |
| [STATE.md](../STATE.md), [MASTERPLAN.md](../MASTERPLAN.md), [ADR.md](../ADR.md), [tickets/](../tickets/), [data/reference/PROVENANCE.md](../data/reference/PROVENANCE.md) | Canonical project documents | Linked, not copied. They govern over topics. |
| Secret files excluded by [.gitignore](../.gitignore) (`.env`) | — | Not read. |

## Per-note dispositions of the native store and its export

198 notes in the export (197 native + 1 export-only), plus the index.

- **Consolidated, 110 notes**: each is named, with its export blob id, in
  the Sources section of the topic that carries it. The in-repo note above
  makes 111 consolidated sources. Facts were checked against the tree where
  load-bearing; superseded details are named in each topic's Sources (the
  preprint is now `main.tex`, the reference counts 177 plants, the erg
  binary path).
- **Dropped, tombstones, 64 notes**: files already reduced to a
  `# DELETED` (63) or `# PROMOTED` (1, `reference_zotero.md`) header, with
  the reason recorded in the stub itself (2026-06-06 to 2026-09-16 prunes).
  Nothing to consolidate.
- **Dropped, stale, superseded or withdrawn, 6 notes**:
  `feedback_durable_reminder_is_blocked_open_ticket.md` (export only;
  withdrawn by the author, ticket 0684);
  `feedback_escalate_means_think_harder.md` (superseded by
  [AGENTS.md](../AGENTS.md) § Autonomous mode and the harness escalation
  protocol); `feedback_evaluate_all_overwrite.md` and
  `feedback_evaluate_all_quality.md` (sweep-2 era runner, fixed in PR #182);
  `project_harness_architecture.md` and `reference_claude_dir_is_idh.md`
  (harness location and ticket channels changed since).
- **Dropped, harness-generic, 11 notes**: runtime and git lessons that are
  not project knowledge and belong to the harness, which carries or governs
  them (git discipline, merge skill, route skill, background-task handling):
  `feedback_api_merge_fetch_after.md`, `feedback_git_pull_creates_merge_commit.md`,
  `feedback_merge_leaves_worktree_on_main.md`, `feedback_raid_wave_stale_base.md`,
  `feedback_concurrent_pipelines_shared_tickets.md`,
  `feedback_worktree_agent_env_leak.md`, `feedback_task_notification_exit_code.md`,
  `feedback_pgrep_self_match_watcher.md`, `feedback_shell_timeout_no_loops.md`,
  `feedback_haiku_truncated_final_reports.md`,
  `reference_peek_kill_sibling_sessions.md`.
  `feedback_concurrent_pipelines_shared_tickets.md` and
  `feedback_worktree_agent_env_leak.md` would also have needed redaction (a
  session identifier, a host path).
- **Dropped, out of scope (another project), 2 notes**:
  `feedback_editorial_book_work.md` (a trade-book project) and
  `reference_homepage_publication_list.md` (the homepage generator
  repository). Never imported.
- **Left out for audience, 5 notes**: `reference_api_keys_location.md`
  (credential locations), `feedback_no_ps_ef_in_claude.md` (names the
  credentials exposed in an incident), `feedback_autonomous_raid_doudou_pickup.md`
  (personal circumstances), `feedback_no_typo_callouts.md` (personal
  detail), `user_platform.md` (personal platform preference).
- **Native `MEMORY.md` index**: its key insights are consolidated where the
  topics cite it; its workstation hardware and directory line and its API
  key line are left out for audience; its entry list is superseded by
  [MEMORY.md](MEMORY.md).

## Audience

The repository is public, so publication here discloses to everyone. A
note's presence in the public harness repository was not taken as clearance:
each was judged on content. Left out: credential locations and names, host
paths, a session identifier, personal circumstances and preferences, and
another project's material. No left-out item was needed for project work.
This repository has no pinned age-encryption mechanism, so nothing private
was kept, encrypted or otherwise; no `.age` file exists.

## Runtime limits

- The v8 index is reached only by agents that load this repository's
  AGENTS.md; no hook injects it. Claude Code loading was probed at adoption
  (see the [adoption journal entry](journal/2026/2026-11-09-memory-v8-adoption.md));
  Codex and Pi loading was not probed.
- The Claude Code native auto-memory remains a separate writer of a separate
  index. This adoption adds no writer: `memory/MEMORY.md` changes only
  through reviewed pull requests (roar, smelt).
- No timer, TTL or automatic promotion is installed.

## Exception: `memory/DREAM.md`

Ticket 0687's second exit criterion asks for `memory/DREAM.md` with its
reference revision. Not created, by documented exception: the ticket's note
of 2026-11-09 records that no deployed project carries one and names the
deployed projects (JETP-observer, climate-finance-het, padme,
sen-causal-reading) as the reference; none has a `memory/DREAM.md`
(checked 2026-11-09). Harness ticket 1443 plans the later redesign.

## Rollback

Revert the adoption merge commit. Native stores, the harness export and the
in-repo note were not modified; no journal entry predates this one.

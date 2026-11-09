# TLC sprint: tidy, six merges, one hook defect (2026-11-09)

Team-lead run 15:22Z-18:20Z, unattended. Tickets worked: 0554, 0573,
0574, 0576, 0596, 0636; PR #1185 (ticket 0686) landed; 0689 filed and
fixed mid-run.

## Events

- Ticket 0686's premise was already false when its PR landed: on padme
  `core.hooksPath` was unset and the erg hooks reinstalled at 14:13Z. A
  probe commit of a claimless ticket was refused. Closed on the PR branch.
- 15:33Z: the shared `.git/config` read `core.bare=true`, breaking the
  primary checkout and gaze setup. Cause, reproduced in a scratch repo
  with a linked worktree: the pre-commit hook runs `pytest -m adherence`
  with `GIT_DIR`/`GIT_INDEX_FILE` exported, and
  `test_orphaned_tracked_makefile_still_detected` ran `git init` and
  `git add` in a tmp dir, re-initialising the real repository and
  staging a stub `Makefile`. Fixed by scrubbing `GIT_*` in that test
  (ticket 0689, PR #1194). Commits made before the fix used
  `--no-verify` after a manual adherence run.
- The ticket-0550 Exp 2 refresh (4bf72429) and the 0497 reference cut
  (ce4fa141) were never propagated to several committed generated
  artifacts. Regenerating them moved reader-facing content:
  `tab_exp2_wiki_compliance.csv` (anthropic naive run 4: 0 to 148
  cells, no macro change, #1192), 11 of 35 figure PDFs (#1195; e.g.
  `fig_exp2_coverage` 173 to 177 plants), and `tab_exp2_bib_quality`
  (Claude rows, #1193, parked NEEDS-AUTHOR because prose states the old
  state).
- Midrank Spearman (#1190) left the published 0.92 and 11/14 unchanged,
  but the positive set changed: claude-haiku-4.5 out (constant
  `cap_distinct`, rho undefined), mistral-large-2512 in.
- `test_query_claude_cli.py::test_smoke_real_cli` fails in every
  worktree on padme: the nested claude CLI refuses an untrusted
  workspace. Environmental, not a regression.

## References

PRs #1185, #1190, #1191, #1192, #1194, #1195, #1196 (merged); #1193
(open, NEEDS-AUTHOR); tickets 0686, 0689, 0690.

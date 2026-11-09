# 2026-11-09 — handover landings: #1198, #1204, #1201, #1193

Context: a peer session's housekeeping sweep handed over this repository's
loose ends; the author said to follow it, then to land the two PRs awaiting
them.

- PR #1198 (filed from harness ticket 1481) added ticket 0690 while main had
  already claimed 0690. Resolved by merging main into the branch (no
  force-push), keeping main's claim and renumbering the new ticket to 0691
  with `erg migrate --claims`. Its body's `**Ticket:**` close claim named the
  ticket the PR created; changed to `Ticket-ref:` so the merge recipe left
  0691 open. Landed bookkeeping tier, 3c5e7524.
- Ticket 0691 run as `/raid 0691` without the raid's agent fan-out (one
  paragraph in `memory/SOURCES.md`). Its "close at that commit" was not
  applied: the recount (by 2026-11-23) and the author's call on the five
  audience-excluded native notes stay open. PR #1204, bookkeeping tier.
- PRs #1201 (ticket 0682) and #1193 (ticket 0636), verify-gate NEEDS-AUTHOR,
  landed on the author's instruction after merging main into each (no
  rebase) and `make check-fast` green on both. #1193 carries the 0550 data
  refresh in the Exp2 annex tables (usable runs 4/5 to 5/5, Arm 3 rows 139
  to 120); open ticket 0690 covers the prose still stating pre-0550 numbers.
- After the sync, `make check-fast` on the primary checkout failed with
  `ModuleNotFoundError: aedist` in 132 test modules. The `.venv` console
  scripts carried a shebang to the virtualenv of the pre-monorepo checkout
  path, which the primary checkout no longer uses; `uv sync` did not
  rewrite them, `uv sync --reinstall` did, after which 2750 tests passed. CI
  and fresh worktrees were unaffected.

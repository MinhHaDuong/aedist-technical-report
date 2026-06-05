Last updated: 2026-06-05T14:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint from the talk manuscript (0435)

WP = `slides/manuscript/main.md`, no restructure; acknowledgements wording blessed; comments absorbed via the perimeter tickets. 0171 cross-eval OUT (journal delta, deferred).

## Current goal — endgame of the 2026-06-05 sprint

22 PRs merged today: de-hazard chain complete (0383→0384/0385/0386+0431, mart reference-stamped schema v2), annex live (0373 matrix + 0434 table, FR), FP-red repo-wide, render DAG guarded (0436/0440), 0254 stats section in, 11 stale tickets closed. Remaining critical path: merge #760 (0416, under gate) → resnap PR (branch `data/resnap-2026-06-05-err510-fix` pushed; must flip #760's refusal test) → **0413 adoption v2** → DAG regeneration → 0255–0262 arbitrage → 0435 finalization.

## Status
<!-- generated 2026-06-05T14:00Z -->

**Tickets:** ~55 ready · ~20 blocked — `erg ready tickets/` for full list
**Recent commits:** 22 merges on 2026-06-05 (PRs #728–#759) — see `git log origin/main`

## In flight (2026-06-05 afternoon)

- Gate #760 (0416 aggregator): independent v1↔v2 accounting recount + status-collapse adjudication.
- MASTER DELETED upstream: sole fixed copy = snapshot on the resnap branch (full 14-sheet clone). Restore: `git show origin/data/resnap-2026-06-05-err510-fix:data/reference/raw/pipeline-2026-06-05.ods > <master path>`.
- Mart staleness hazard (0383) RETIRED — mart current, guarded, reference-stamped.

## Backlog / deferred

- Follow-ups open: 0441 (bib table FR), 0442 (extraction capacity validator), 0443 (no-name-synthesis ratchet), 0377 (chore-filter bug confirmed live).
- 0255–0262 Exp2 sections — arbitrate after reading 0254's landed section.
- Post-preprint: research track 0396–0400, level 0401/0402, GEM 0428/0429, 0171.
- 0389 EN→FR slides script in flight; consider a master-backup-discipline ticket (single-copy master nearly lost today).

Last updated: 2026-06-05T14:55Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint from the talk manuscript (0435)

WP = `slides/manuscript/main.md`, no restructure; acknowledgements wording blessed; comments absorbed via the perimeter tickets. 0171 cross-eval OUT (journal delta, deferred).

## Current goal — endgame of the 2026-06-05 sprint

24 PRs merged today: de-hazard chain complete (mart reference-stamped schema v2), annex live (matrix + table, FR), 0416 aggregator (#760), clean snapshot resnap (#764: 170 plants, green end-to-end). Remaining critical path: **0413 adoption v2** (running) → DAG regeneration → 0255–0262 arbitrage → 0435 finalization.

## Status
<!-- generated 2026-06-05T14:00Z -->

**Tickets:** ~55 ready · ~20 blocked — `erg ready tickets/` for full list
**Recent commits:** 22 merges on 2026-06-05 (PRs #728–#759) — see `git log origin/main`

## In flight (2026-06-05 afternoon)

- MASTER DELETED upstream: sole fixed copy = the committed snapshot (full 14-sheet clone), durable on main (#764, 147343 bytes verified). Restore: `git show origin/main:data/reference/raw/pipeline-2026-06-05.ods > <master path>`.
- Mart staleness hazard (0383) RETIRED — mart current, guarded, reference-stamped.

## Backlog / deferred

- Follow-ups open: 0441 (bib table FR), 0442 (extraction capacity validator), 0443 (no-name-synthesis ratchet), 0377 (chore-filter bug confirmed live).
- 0255–0262 Exp2 sections — arbitrate after reading 0254's landed section.
- Post-preprint: research track 0396–0400, level 0401/0402, GEM 0428/0429, 0171.
- 0389 EN→FR slides script in flight; consider a master-backup-discipline ticket (single-copy master nearly lost today).

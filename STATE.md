Last updated: 2026-06-04T20:30Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Post-conference — paper writing runway

Econom'IA 2026 talk delivered at Thema/Cergy 2026-05-27. Next: write the paper.

## Current goal

Write the Exp 2 paper sections (0251–0262) and finish cross-eval scoring (0171). `slides-en.tex` is the single source of truth for slide prose; `slides.tex` (FR) is a derived translation (script in flight, 0389). Clean-room writing build landed (0352/0370): `make report` / `make slides` carry no `uv run`, guarded by adherence tests.

## Status
<!-- generated 2026-06-04T20:30Z -->

**Tickets:** ~54 ready · ~23 blocked — `erg ready tickets/` for full list
**Recent commits:**
  bb2f3a80 ticket(0412): close and archive — HAL validation confirmed
  1547af23 ticket(0420): close and archive — PR #711
  811a16ed test(0423): guard — empty raw-reply wildcard with non-empty archive sibling

## Workplan

1. Experiments, conference, clean-room build split — DONE (see git log).
2. Paper writing — ACTIVE: Exp 2 sections (0251–0262), cross-eval scoring (0171).
3. Reference pipeline v2 — 0420/0419 merged (raid 2026-06-04); 0416 next, then 0413 adoption.

## Night raid queue (2026-06-04, curated)

Wave A: 0416 → 0401 (aggregator, then level schema; Blocked-by set). Wave B: 0253 + 0254 (Exp2 sections, parallel-safe). Filler: 0403, 0425.
Excluded on purpose: 0171 (API spend), 0383 (rewrites committed scores), 0398/0399 (need Imagine scoping), 0412 (closed). Launch: `/raid 416 401 253 254 403 425`.

## Backlog / deferred

- 0389 EN→FR slides script in flight; 0360 reproducibility oracle; 0364 (default won't-do).
- Research track 0396–0400 — needs scoping into bounded sub-tickets.
- Hygiene: `origin/chore/restore-panel-state` + local `ticket/0345` need manual review before deletion.
- Mart staleness (0383): full-DAG runs rewrite committed scores until 0384–0386 lands — don't run analysis targets casually.

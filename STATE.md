Last updated: 2026-05-27T09:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Post-conference — paper writing runway

Econom'IA 2026 talk delivered at Thema/Cergy 2026-05-27. Next: write the paper.

## Current goal

Merge open PRs (#606 slides 0347, #612 spider 0348), re-enable CI, then open paper-writing tickets.

## Status
<!-- generated 2026-05-27T09:00Z -->

**Tickets:** 29 ready · 20 blocked — `erg ready tickets/` for full list
**Recent commits:**
  1e1006bc slides(exp1): add hallucination examples slide after figure overlay
  acd8d613 state: 0345 DAG done; mark stale remote branch for end-session prune
  6d6ee192 tickets(0352,0353): tag deferred — post-conference follow-ups
  4ffe7107 slides: rename FP category Connaissance périmée → Référence inexacte
  68a0876b slides(discussion): add FP typology slide; rename hallucinées → non-reconnues

## Workplan

1. **Experiment 3 runs.** DONE.
2. **Experiments analysis.** DONE — Exp 1/2/3 figures produced, take-home messages A–D ratified.
3. **Update manuscript.** DONE — 0313–0318 closed.
4. **Update slides.** DONE — conference delivered 2026-05-27.
5. **Post-conference cleanup.** IN PROGRESS — merge PRs #606/#612, re-enable CI, prune stale branches.
6. **Paper writing.** Opens next.

## Backlog / deferred

- Scaling-curve diagnosis — direct_complete F1=0 on 3 capable models (parser failure suspected).
- Paper writing opens after post-conference cleanup.
- Report clean-room build + uv-run guard deferred (tickets 0352/0353).
- CI required-checks rule disabled 2026-05-26 — **re-enable now** (talk done).
- Prune stale remote branches: `origin/t0345-collapse-exp2-single-producer`, `origin/score-4-arms-2x2`, `origin/chore/restore-panel-state`.
- `ticket/0345-collapse-exp2-single-producer` local branch has 3 pre-PR commits not in main — manual review before deleting.
- `slides/conference-day-final` needs surgery before PR: drop slides.tex change (keep Préconisation frame), drop Makefile additions (zombie include + duplicates already in main), drop plot_cost_quality/plot_exp2_arms_split/test regressions vs PR #604. Keep: analysis.mk cleanup (finishes 0345), slides/Makefile delegation, .gitignore.

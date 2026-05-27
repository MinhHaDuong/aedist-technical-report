Last updated: 2026-05-27T13:39Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Post-conference — paper writing runway

Econom'IA 2026 talk delivered at Thema/Cergy 2026-05-27. Next: write the paper.

## Current goal

Post-conference slides review done (PRs #615/#616). Open paper-writing tickets.

## Status
<!-- generated 2026-05-27T22:00Z -->

**Tickets:** 29 ready · 20 blocked — `erg ready tickets/` for full list
**Recent commits:**
  4948b617 chore: rebuild exp2 generated artifacts (side effect of analysis.mk)
  c3bbdf83 fix(fig): E1 FP bars on coverage; larger condition labels
  e9dc00e5 fix(slides): rebuild figs 16+17 with restored labels; fix hallucinations term
  25018257 slides: hide RAG table (19), soften conclusions wording
  7e0e386a slides(21): top-align Limites frame content

## Workplan

1. **Experiment 3 runs.** DONE.
2. **Experiments analysis.** DONE — Exp 1/2/3 figures produced, take-home messages A–D ratified.
3. **Update manuscript.** DONE — 0313–0318 closed.
4. **Update slides.** DONE — conference delivered 2026-05-27.
5. **Post-conference cleanup.** DONE — PRs #606/#612/#615/#616 merged, regressions fixed.
6. **Paper writing.** Opens next.

## Backlog / deferred

- Scaling-curve diagnosis — direct_complete F1=0 on 3 capable models (parser failure suspected).
- Paper writing opens now.
- Report clean-room build + uv-run guard deferred (tickets 0352/0353).
- CI required-checks rule disabled 2026-05-26 — **re-enable** (talk done, no longer blocking).
- Stale remote branches to prune: `origin/score-4-arms-2x2`, `origin/chore/restore-panel-state`.
- `ticket/0345-collapse-exp2-single-producer` local branch has 3 pre-PR commits not in main — manual review before deleting.

Last updated: 2026-05-27T21:10Z

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
7. **Report/ablation cleanup.** 0361 + 0362 EXECUTED + closed on branch `claude/pr617-makefile-audit-S4US7` (build-unverified, see Handoff); 0352 unblocked (still `deferred`); 0364 spun off; 0353/0360 still blocked on 0352.

## Handoff — report/ablation cleanup

**Open branch `claude/pr617-makefile-audit-S4US7` (pushed, NOT merged).** Carries: the 0354 duplicate-ID renumber→0363 + erg housekeeping; **0361** (ablation thread retired, verification salvaged to §Perspectives) and **0362** (report Exp2 reframed onto `tab_exp2_2x2`, `fig_quality_spider` retired, dead `tabulate_exp2_arms` removed) — both closed/archived; new ticket **0364**. All code-level work is test-verified (TDD red→green + adherence/DAG/dedup guards, full suite collects clean). **NOT verified: any LaTeX/pandoc compile — this env has no engine.** Before merge: run `make report` + `make slides` + `make check` somewhere with `tectonic`/`pandoc`.

Remaining run order: **0352 → 0353 ∥ 0360**.
- **0352** clean-room report build (no `uv run` in `make report`; migrate the **4 remaining** producers — `tabulate_comparaison`, `tabulate_variance`, `variance_decomposition`, `tabulate_coherence` — into `experiments/analysis.mk` + commit artifacts). Blockers cleared; still `Tag: deferred` (decide whether to un-defer now the cleanup is the active track). TDD gate is engine-free: `make -n report | grep -c "uv run"` (4 now → 0 done). The full clean-room compile needs an engine.
- **0353** no-`uv run` writing-build adherence guard. `Blocked-by: 0352`, `deferred`.
- **0360** clean/cleaner reproducibility oracle (content-diff, **no timestamps**). `Blocked-by: 0352`.
- **0364** (deferred) evaluate renaming the mart `arm1..arm4` terminology to 2×2 cell labels; **default WON'T-DO** (arms = the four cells, load-bearing; rename churns the mart schema for little payoff).

**Findings to carry forward:**
- The "arms" naming is the 2×2's **data foundation** — `plot_exp2_arms_split` (slides coverage/cost figs), `tabulate_exp2_arms_runs` (mart view → 2×2), and `plot_exp2_arms_comparison` (live manuscript `main.md` Fig 3) are all load-bearing. The DAG guard (0363) caught an over-deletion; only `tabulate_exp2_arms` (the report table) was ever dead.
- **Pre-existing `make slides` break** (NOT from this work): `manuscript/main.pdf` needs `../report/inputs/generated/fig_capability_dag.pdf`, but the root `slides/slides.pdf` prereqs list `fig_capability_timeline` instead → recursive sub-make can't resolve it. Worth its own ticket. The union-aware DAG guard can't see it (runtime recursive-make visibility, its known limit).
- 0361 deviation: the census Makefile rule was retargeted to produce `macros_census.tex` (sole producer; slides `\NumCensusModels`); the census figure is now an unconsumed `--output` byproduct.

## Backlog / deferred

- Scaling-curve diagnosis — direct_complete F1=0 on 3 capable models (parser failure suspected).
- Paper writing opens now.
- Report/ablation cleanup: 0361/0362 done+closed on branch `claude/pr617-makefile-audit-S4US7` (needs merge + a LaTeX/pandoc build to confirm); then 0352 → 0353 ∥ 0360; 0364 deferred — see Handoff.
- New ticket candidate: fix the pre-existing `make slides` break (`fig_capability_dag` vs `fig_capability_timeline` recursive-make mismatch).
- Stale remote branches to prune: `origin/score-4-arms-2x2`, `origin/chore/restore-panel-state`.
- `ticket/0345-collapse-exp2-single-producer` local branch has 3 pre-PR commits not in main — manual review before deleting.

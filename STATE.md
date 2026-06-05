Last updated: 2026-06-05T18:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: arXiv preprint (0435)

**The preprint WP is `slides/manuscript/main.md`** — report.tex is internal ("no future", author 2026-06-05). main.md is structurally complete: v2 numbers throughout, Annex E (recognition matrix + status-difficulty table) + Discussion future-work paragraph (#767). Remaining: blessed acknowledgements, full author read, arXiv build, sign-off. 0171 cross-eval OUT (journal delta).

## Status
<!-- generated 2026-06-05T18:00Z -->

**Tickets:** ~50 ready · ~18 blocked — `erg ready tickets/` for full list
**Recent commits:** 28 PRs merged 2026-06-05 (#728–#769) — v2 sprint complete, `make check` green on main

## Sprint 2026-06-05 — CLOSED

Reference v2 (170 plants) adopted end-to-end: snapshot policy → aggregator (#760) → clean resnap (#764, snapshot = sole master copy, durable on main; restore: `git show origin/main:data/reference/raw/pipeline-2026-06-05.ods > <path>`) → adoption (#767: re-score Exp1–3, figures at 170, #547 prose corrected ×3, manuscript annex) → class fix + ratchet ticket (#769, 0447).

## Next actions

1. **0255–0262 arbitrage** — target report.tex; probably moot now (preprint = main.md). Close-or-requalify with author.
2. **0435 finalization** — acknowledgements (blessed wording), author read, arXiv build.
3. Backlog: 0444 (census re-score), 0445 (extension-as-unit, settles 170 vs 174 before macroizing literals), 0446 (matrix figure rework), 0447 (hardcoded-size ratchet), 0441–0443, 0377.

## Open issues

- PRIMARY repo: uncommitted user edits (`experiments/render.mk`, `src/aedist/plot_method_convergence.py`) left untouched; local main FF blocked until resolved.
- Census artifacts rebuild only in the primary checkout (archived outputs invisible from worktrees) — documented limitation, deferral 0444.

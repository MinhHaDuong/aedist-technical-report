# Phase-stratified artifact policy

*Policy note for the AEDIST pipeline. Ratified 2026-06-04 (ticket 0405).
The per-file manifest below is the spec that the per-phase build split
(ticket 0406) enforces structurally.*

## The rule

The pipeline runs in four phases. **Track the OUTCOME of each phase** so
every phase can rebuild without re-running its parent. Every other generated
file is non-precious (regenerable) and is `.gitignore`d.

| Phase | What it does | Outcome (TRACK) | Non-precious (IGNORE) |
|-------|--------------|-----------------|-----------------------|
| **P1 Acquire** | API runs against models (`experiments/Makefile`) | raw model replies: `experiments/outputs/**`, `experiments/archive/**` (incl. extracted `*.md` siblings of tracked `*.json`) | run logs, retries, jobs/, `rag_work/` |
| **P2 Score & consolidate** | extract → evaluate → assemble (all P2 verbs + the mart build in `experiments/derived/score.mk`, invoked from the repo root) | `measurements.jsonl` (mart v0, transitional until 0297), `experiments/derived/exp2_mart.jsonl` | per-run `experiments/derived/**/*.record.json`, mart→view CSVs |
| **P3 Analyze & render** | plot/tabulate scripts (`experiments/render.mk`, including the mart→view projection) | figures/tables/macros the manuscript or slides include: `report/inputs/generated/` (the single P3 deliverable tree; the slides-side tree was retired, 0408) | plotting intermediates consumed only inside P3 (`census_bars.csv`, view CSVs, unconsumed figs; the report-dir `cost_quality.csv` is a P4 prereq → tracked) |
| **P4 Write** | tectonic / pandoc (`report/Makefile`, `slides/Makefile`) | — (final PDFs are regenerable) | `report.pdf`, `slides.pdf`, LaTeX aux files |

## The classification test

For any generated file, find its **producing rule** and its **consuming
rule(s)** in the Makefile DAG (`Makefile`, `experiments/Makefile` for P1,
`experiments/derived/score.mk` for P2, `experiments/render.mk` for P3,
`experiments/paths.mk` for shared variables, `report/Makefile`,
`slides/Makefile`):

- **Producing phase ≠ consuming phase → boundary outcome → TRACK.**
- **Same phase, or no consumer at all → intra-phase intermediate → IGNORE**
  (`git rm --cached`, keep the working-tree copy and the ignore line).
- A file consumed in *both* its own phase and a later phase: the boundary
  classification wins (TRACK).

"Consumer" means an actual read by a downstream rule's recipe — an
`\input`/`\includegraphics` in a P4 `.tex`/`.md`, or a CLI `--input` in a
later-phase script. A path merely listed as a `make` prerequisite but never
read (e.g. an over-declared prereq) is **not** a consumer.

The adherence test `tests/test_no_tracked_ignored_files.py` enforces the
invariant mechanically: `git ls-files -i -c --exclude-standard` must stay
empty, so no file is ever tracked and ignore-matched at the same time.

## Notes on transitional / special cases

- **`measurements.jsonl`** is mart v0 — a P2 outcome, transitional until
  ticket 0297 retires it. It stays tracked and is **not** moved.
- **mart → view CSVs** (`*_view.csv`) are P3 projections of the mart, consumed
  only inside P3 plotting/tabulating. They stay ignored.
- **`report/inputs/generated/` figure PDFs** are tracked uniformly via the
  directory-scoped negation `!report/inputs/generated/*.pdf`. This directory
  is the analysis→writing handoff surface; its figure PDFs are P3→P4 boundary
  outcomes. Two of them (`fig_exp2_turn_trajectory.pdf`, `fig_quality_spider.pdf`)
  have no current P4 consumer — they are produced into the handoff directory
  ahead of the (exploratory) prose that will include them, so the directory
  policy tracks them rather than churning the index each time prose catches up.
- **Single P3 deliverable tree (0408).** The slides-side generated tree
  (`slides/inputs/generated/`) is retired: P3 now writes every figure/table/macro
  into the one tree `report/inputs/generated/`, and the slides build consumes
  them from there
  via `../report/inputs/generated/`. The two slide-only `.tex` outcomes moved
  with a rename to avoid colliding with the report variants of the same name:
  `macros.tex → macros_slides.tex` (census-flavoured macros) and
  `tab_exp2_2x2.tex → tab_exp2_2x2_fr.tex` (the FR table). The slide-side
  figures that had no P4 consumer (`fig_regimes_scatter.pdf`,
  `fig_scaling_curve.pdf`, `fig_method_convergence.pdf`) keep their producer
  rules, now writing into the report tree. They are not committed (no
  regeneration here — mart-staleness hazard, 0383); a clean checkout has no
  working-tree copy. The slides-dir `cost_quality.csv` copy is dropped (the
  report-dir `cost_quality.csv` already serves every consumer). (The
  **report**-dir `cost_quality.csv` *is* a P4 prerequisite of
  `manuscript/main.pdf` via `slides/Makefile` → tracked.)

## Manifest (the 22 reconciled files)

The 22 files that were previously tracked **and** ignore-matched, with their
producer phase, consumer, and verdict.

| File | Producer (phase) | Consumer (phase) | Verdict |
|------|------------------|------------------|---------|
| `report/inputs/generated/fig_capability_dag.pdf` | `plot_capability_dag` (P3) | slides manuscript (P4) | TRACK |
| `report/inputs/generated/fig_capability_timeline.pdf` | `plot_capability_timeline` (P3) | slides.tex / manuscript (P4) | TRACK |
| `report/inputs/generated/fig_direct_cost_quality.pdf` | `plot_cost_quality` (P3) | manuscript (P4) | TRACK |
| `report/inputs/generated/fig_direct_p1_base.pdf` | `plot_method_convergence` (P3) | slides.tex / manuscript (P4) | TRACK |
| `report/inputs/generated/fig_exp2_arms_comparison.pdf` | `plot_exp2_arms` (P3) | manuscript (P4) | TRACK |
| `report/inputs/generated/fig_exp2_cost.pdf` | `plot_exp2_arms_split` (P3) | slides.tex (P4) | TRACK |
| `report/inputs/generated/fig_exp2_coverage.pdf` | `plot_exp2_arms_split` (P3) | slides.tex (P4) | TRACK |
| `report/inputs/generated/fig_exp2_coverage_certainty.pdf` | `plot_exp2_*` (P3) | slides.tex / manuscript (P4) | TRACK |
| `report/inputs/generated/fig_exp2_turn_trajectory.pdf` | `plot_exp2_turn_trajectory` (P3) | none yet (handoff dir) | TRACK (dir policy) |
| `report/inputs/generated/fig_quality_spider.pdf` | `plot_quality_spider` (P3) | none yet (handoff dir) | TRACK (dir policy) |
| `report/inputs/generated/fig_spider_cross_exp.pdf` | `plot_spider_cross_exp` (P3) | slides.tex (P4) | TRACK |
| `report/inputs/generated/fig_spider_exp1_claude.pdf` | `plot_spider_exp1` (P3) | slides.tex (P4) | TRACK |
| `report/inputs/generated/fig_spider_exp1_families.pdf` | `plot_spider_exp1` (P3) | report.tex / slides.tex / manuscript (P4) | TRACK |
| `report/inputs/generated/macros_p1_base.tex` | `plot_method_convergence` (P3) | report.tex / slides.tex (P4) | TRACK |
| `report/inputs/generated/macros_slides.tex` (was `slides/.../macros.tex`, renamed 0408) | `tabulate_macros --census-csv` (P3) | slides.tex (P4) | TRACK |
| `report/inputs/generated/tab_exp2_2x2_fr.tex` (was `slides/.../tab_exp2_2x2.tex`, renamed 0408) | `tabulate_exp2_2x2 --lang fr` (P3) | slides.tex (P4) | TRACK |
| `experiments/outputs/sota_exp3_arm3_batch1/archive/run02_rerun_mistral_20260525T0521_local/mistral.md` | API run extraction (P1) | provenance sibling of tracked `mistral.json` | TRACK (exact-path negation) |
| `report/inputs/generated/cost_quality.csv` | `plot_cost_quality` (P3) | `manuscript/main.pdf` via slides/Makefile (P4) | TRACK |
| `slides/inputs/generated/cost_quality.csv` (slide copy) | analysis copy (P3) | none in P4 | RETIRED 0408 — copy rule dropped |
| `slides/inputs/generated/fig_regimes_scatter.pdf` | `plot_regimes_scatter` (P3) | none in P4 | RETIRED 0408 — producer redirected to report tree |
| `slides/inputs/generated/fig_scaling_curve.pdf` | `plot_scaling_curve` (P3) | none in P4 | RETIRED 0408 — producer redirected to report tree |
| `derived/fusion_proto/growth_curve.pdf` | none (orphan prototype) | none | IGNORE (`git rm --cached`) |

## Spot-check coverage (other generated paths in the DAG)

| File | Phase | Verdict | Why |
|------|-------|---------|-----|
| `measurements.jsonl` | P2 outcome | TRACK | mart v0, transitional (0297) |
| `experiments/derived/exp2_mart.jsonl` | P2 outcome | TRACK | consolidated mart |
| `experiments/derived/**/*.record.json` | P2 intermediate | IGNORE | per-run scoring sidecars, regenerated |
| `report/inputs/generated/census_bars.csv` | P3 intermediate | IGNORE | feeds `tabulate_macros` (same phase) |
| `report/inputs/generated/exp2_mart.jsonl` | P3 staging copy | IGNORE | mart staged into report dir, not handoff |
| `report/inputs/generated/*_view.csv` | P3 intermediate | IGNORE | mart→view projections |
| `report/inputs/generated/tab_*.tex` (non-ignored) | P3 outcome | TRACK | `\input` by report.tex (already tracked, not ignore-matched) |
| `report.pdf`, `slides.pdf` | P4 final | IGNORE | regenerable from tracked P3 outcomes |

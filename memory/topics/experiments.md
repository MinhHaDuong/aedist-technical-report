# Experiments — design and records

Scope: the design choices of the experimental programme that are not
re-derivable from the manuscript alone. Specs of record are the tickets
named below; numbers come from `measurements.jsonl` and the generated
artifacts, never from this page.

## Programme

Three experiments plus a case study, presented at Econom'IA 2026
(2026-05-27; abstract in `docs/HaDuong-2026-EconomIA-Abstract.md`).
Exp 1 = parametric baseline; Exp 2 = SOTA frontier deep research; Exp 3 =
reconstruction from a verified bibliography; case study (0200) = the
stateful production demonstration.

## Experiment 1 — parametric baseline

- Measures the best row-level F1 from model memory alone. The constraint is
  **no web**, set in the sweep's `system_instruction`; **thinking is
  allowed** (part of the parametric capability). Do not propose
  `no_think=true` for Exp 1 (author, 2026-05-21).
- Baseline prompt = modules 2+5 (goal + table, no persona), so the persona
  effect is measurable. Modules use the numbered scheme `1_persona` …
  `6_bibliography`, `A_Statistics` … `D_Completeness`.
- Closed 2026-05-21: 16 models × 5 reps (note). The note's output path
  `experiments/outputs/ablation/direct/p1_base/` and set
  `modelset_ablation_journal` no longer exist (checked 2026-11-09). The
  journal baseline is now `[sweeps.sweep_exp1_baseline]` on
  `[sets.modelset_exp1_journal]` in `experiments/experiments.toml`, its
  outputs archived under `experiments/archive/outputs/exp1/baseline/`;
  use the pinned set, do not recompute the lineup from the registry.

## Experiment 2 — two arms

- Same 4 agents, 5 reps each: *naive* (single-shot prompt, web on, the
  comparator) and *optimized* (meta-prompt + multi-turn state machine).
  The contrast isolates the protocol's contribution.
- Cross-evaluation (Phase C, ticket 0171) scores **both** arms plus the
  Exp 1 baseline as control; never scope it to one arm.
- Optimized-arm outputs for analysis:
  `experiments/archive/outputs/sota_exp2_brerun1/` (ticket 0243; archived
  from `experiments/outputs/`, checked 2026-11-09). `sota_exp2_phase_b_full/`,
  archived beside it, used the wrong classifier and has routing errors: do
  not analyse it.

## Experiment 3 — reconstruction

Design locked in ticket 0202 (closed): start from the cheapest Exp 2 output
(overview + bibliography only); three-tier human-in-the-loop verification
of sources; five strategies (null, batch RAG, incremental chronological /
random / embedding-ranked); state = a structured working report, not a
growing raw context. Read 0202 before any Exp 3 work; do not re-litigate
the strategy list, protocol, ranker or rep count.

## Standing design choices

- Pair one local model with one frontier cloud model through every sweep:
  "can local do it?" is a research question of the report (feasibility for
  countries with limited resources).
- "Test one before blasting" holds at experiment level too: run one rep per
  condition before N reps (rule: [.claude/rules/workflow.md](../../.claude/rules/workflow.md)).
  MoE cloud sweeps need `repeat=3`
  ([.claude/rules/experiment-design.md](../../.claude/rules/experiment-design.md)).
- A small local 9B model reached F1 0.984 on direct extraction
  (2026-04-30, n=1, coal-heavy subset suspected): replicate and check for
  leakage before scoping any local deep-research stack on it. Replication
  status not checked at adoption.

## Sources

- Native notes: `project_exp1_design_thinking_allowed.md` 7177886f,
  `project_exp1_module_scheme.md` 0b2aeacb, `project_exp1_done.md` be5086e8,
  `project_exp2_phase_b_done.md` f1d9bf04, `project_exp3_reconstruction_sweep.md` a3e5c44f,
  `project_talk_narrative_three_plus_case_study.md` bba52333,
  `reference_econom_ia_2026.md` 6d3d74d1, `feedback_local_vs_cloud.md` 3130aa29,
  `feedback_test_one_before_blasting_experiment_level.md` 17b5ffe4,
  `project_local_9b_near_ceiling.md` d937d9e5.
- Checked 2026-11-09: tickets 0200 and 0202 closed, 0171 open.

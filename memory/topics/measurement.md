# Measurement — quality frame, scoring and statistics

Scope: how results are scored and read. Contracts of record:
`docs/scoring-contract.md`, ADR-7 in [ADR.md](../../ADR.md), and the
manuscript's §2 quality bar.

## Quality frame

- Three qualities (resolved 2026-04-30): **data** quality (limits:
  coverage, freshness), **answer** quality (limits: articulation,
  coherence), **method** quality (verifiable / verified provenance).
  Method quality is perpendicular to the four limits, not a fifth limit;
  agents and agent teams enter through it.
- Coherence is built bottom-up as reference-free indicators (0201 → 0396 →
  0397): per-field fractions stay as the breakdown; composites
  `coherence_internal` / `coherence_external` use **per-row pass/fail**, so
  a bad row counts once. The objective is reference-free production, where
  a non-atomic (1NF-violating) row is a defect; do not conflate it with the
  reference-based matching objective of 0393. Capacity plausibility is
  level-conditional (Level dimension, 0401/0402), never a flat ceiling.

## Reading scores

- `f1=None` is a non-attempt (refusal, or no usable inventory), not zero:
  exclude it from means and report n_valid / n_total.
- **Refusal is data**: a principled decline is classified and reported
  ("declined" in manuscript tables), not rerun or engineered away.
- Presence metrics (source present, field complete) saturate at 1.0 in
  parametric runs, since models fill every requested column; prefer metrics
  of diversity or validity.
- LP-irreconcilable false positives are "unrecognized" ("non-reconnus"), not
  "hallucinated": many are real plants under name variants the matcher
  missed. Reserve "hallucination" for clear inventions.
- `model_family()` puts `gpt-oss-*` in the gpt family: never label a panel
  split "closed-source" vs "open-weight" by family; enumerate families.

## Statistics

- With n=3 runs, bootstrap CIs on F1 are about ±5–8 pp; 5 reps for models
  within 5 pp of each other, 3 suffice beyond 15 pp. `repeat` is a per-sweep
  field in `experiments.toml`.
- A one-sided sign-flip permutation test on n subjects cannot reach
  p < 1/2^n: with n=4, p < 0.05 is unreachable.

## Scoring-code facts

- Multi-turn extraction joins all assistant turns; the best table is often
  not in the last one.
- Responses may carry several pipe tables: split them and score each
  candidate.
- Per-string normalisation (e.g. unit-suffix stripping) derives its rule
  from the fixed reference, not from the input frame.
- Sort keys derived from a model attribute (`size_class`) resolve once per
  model: reps of one model may carry different values.
- `tab_exp2_arms_runs.csv` has no `n_matched`; use the `_view` variant.

## Sources

- Native notes: `project_three_quality_argument.md` 77b7d373,
  `project_coherence_axis_decomposition.md` 4fc95161, `project_f1_none_semantics.md` 31e5be5d,
  `feedback_refusal_is_data.md` 78fdc9bb, `feedback_presence_metrics_saturate.md` e20046cd,
  `feedback_fp_unrecognized_not_hallucinated.md` 4bb227e3, `project_gpt_oss_family.md` 80bd17da,
  `feedback_permutation_test_power.md` f0fd1203, `feedback_multiturn_all_turns.md` f3f5f0b9,
  `feedback_pipe_table_splitting.md` 4088da76, `feedback_unit_suffix_stripping_design.md` 1e034c26,
  `feedback_size_class_per_record_split.md` 6054021e, `feedback_arms_runs_csv_no_nmatched.md` 6c847b6f.
- In-repo untracked note `project_statistical_power.md` (git-ignored
  `.claude/projects/` directory of the primary checkout; see
  [SOURCES.md](../SOURCES.md)).
- The three-quality note named `docs/measurement-framework.md`, absent from
  the tree on 2026-11-09; the frame is restated here from the note.

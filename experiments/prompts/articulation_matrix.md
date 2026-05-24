# Articulation Matrix for Mechanical Scoring v1

Scope: ticket 0272 for the 0270 family. v1 scoring is Exp2-first. Exp1 is
included here as a reference case to document which future Exp1 metrics must be
null/annotated rather than interpreted as model failure.

Definitions:
- `asked_explicitly`: the field or column is requested directly in prompt instructions
- `implied`: the field is supported by surrounding guidance, but not requested as a formal field/column
- `absent`: the field is not requested in a way that supports scoring it

Prompt surfaces in scope:
- `exp1_table_module`: `experiments/prompts/modules/5_table.txt`
- `exp2_naive`: `experiments/sota/protocol_07_naive_prompt.md`
- `exp2_design`: `experiments/sota/protocol_02_metaprompt.md`

| Metric family | Required field(s) | Exp1 table module | Exp2 naive | Exp2/3 design | Notes |
|---|---|---|---|---|---|
| Accuracy: inventory recall / precision (`acc_tp`, `acc_fp`, `acc_fn`, `acc_f1`) | one row per in-scope asset; stable plant identity columns | asked_explicitly | asked_explicitly | asked_explicitly | All three prompts ask for a complete thermal inventory table. Exp2 naive and Exp2 design also state row-level F1 as an evaluation target. |
| Coherence: no duplicate asset rows (`coh_no_duplicate_frac`) | stable row identity / one-row-per-asset expectation | implied | implied | asked_explicitly | `protocol_02_metaprompt.md` explicitly defines row granularity. Exp1 and Exp2 naive imply uniqueness through the requested plant table but do not state a deduplication rule. |
| Coherence: controlled vocab adherence (`coh_vocab_adherent_frac`) | Fuel, Technology, Status vocabularies | asked_explicitly | asked_explicitly | asked_explicitly | All three prompts specify the fuel/technology/status schema directly. |
| Coherence: high-confidence rows should be dual-sourced (`coh_high_conf_dual_sourced_frac`) | Confidence, Source 1, Source 2 | absent | implied | implied | Exp1 lacks the Confidence column entirely. Exp2 prompts explicitly ask for Confidence and Source 1/2, and provenance guidance implies stronger evidence for higher-confidence rows, but they do not literally require two sources for every HIGH row. Future Exp1 scoring must annotate this as `prompt_not_asked`. |
| Provenance: rows with two sources (`prov_dual_source_frac`) | Source 1, Source 2 | asked_explicitly | asked_explicitly | asked_explicitly | All three prompts request two source columns. |
| Provenance: Source 1 primary-source rate (`prov_primary_s1_frac`) | Source 1 plus source hierarchy guidance | absent | implied | implied | Exp1 asks for sources but does not define a primary/secondary hierarchy. Exp2 prompts define provenance and source hierarchy strongly enough to support this metric. Exp1 rows would need annotation rather than direct comparison. |
| Temporality: status as-of present (`temp_asof_present_frac`) | Status as-of-date | absent | asked_explicitly | asked_explicitly | Exp1 has Status but no Status as-of-date field. Future Exp1 scoring must annotate this as `prompt_not_asked`. |
| Temporality: status as-of plausible (`temp_asof_plausible_frac`) | Status as-of-date | absent | asked_explicitly | asked_explicitly | Same articulation gap as above. |
| Field completeness: capacity present (`fc_capacity_present_frac`) | Total MWe | asked_explicitly | asked_explicitly | asked_explicitly | All prompts require Total MWe in the plant table. |
| Field completeness: COD plausible (`fc_cod_plausible_frac`) | COD | asked_explicitly | asked_explicitly | asked_explicitly | All prompts request COD. Exp1 uses "actual or expected commercial operation date"; plausibility still needs scorer-side date handling, not prompt changes. |
| Field completeness: province present (`fc_province_present_frac`) | Province | asked_explicitly | asked_explicitly | asked_explicitly | Province is present in all table schemas. Exp1 mentions it only as a column, not a narrative emphasis, but that is still explicit enough for scoring. |

## Exp1 absent-cell interpretation

The following metrics are not directly scoreable on current Exp1 outputs without
annotation:

- `coh_high_conf_dual_sourced_frac` because Exp1 does not ask for `Confidence`
- `prov_primary_s1_frac` because Exp1 does not specify a source hierarchy
- `temp_asof_present_frac` because Exp1 does not ask for `Status as-of-date`
- `temp_asof_plausible_frac` because Exp1 does not ask for `Status as-of-date`

For any future mixed Exp1/Exp2 result table, these should be represented as
null with a `prompt_not_asked` annotation rather than as zero-valued failures.

## Upstream verification spot check

Verification surface:

- metadata files: `experiments/outputs/sota_exp2_naive_arm/openai_run01.json`, `experiments/outputs/sota_exp2_brerun1/openai_run01.json`
- rendered outputs: `experiments/outputs/sota_exp2_naive_arm/openai_run01.md`, `experiments/outputs/sota_exp2_brerun1/openai_run01.md`
- independent extraction path: `extract._extract_pipe_tables()` + `score_csv_like_block()` + `parse_and_canonicalize()`
- tabulated row proxy: `tabulate_exp2_arms_runs._count_md_table_rows()` for naive arm; `inventory_rows` field in optimized metadata

Observed results:

| Arm | Sample | Independent extracted plant rows | Current inventory_rows proxy | Outcome |
|---|---|---:|---:|---|
| naive | `openai_run01` | 79 | 118 | mismatch |
| optimised | `openai_run01` | 83 | 122 | mismatch |

Diagnosis:

1. The markdown outputs contain one large plant table plus several summary tables.
2. The independent extraction path selects the best plant-table candidate.
3. The current `inventory_rows` proxy counts every pipe-table row in the markdown,
   including summary tables, so it is not a stable proxy for plant-table rows.

Implication for the 0270 family:

- Path resolution is fine for the sampled runs.
- Plant-table row parity does **not** currently hold between scorer-style extraction
  and `inventory_rows`.
- Ticket 0277 owns the upstream bugfix: revise row-count logic so it targets the
  plant table rather than all markdown tables.
- Ticket 0275 then consumes that corrected upstream meaning for ingestion parity
  and parser reuse work.
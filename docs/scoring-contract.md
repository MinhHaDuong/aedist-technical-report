# Mechanical Scoring Contract — v1

**Scope:** Exp2 outputs (naive arm and optimised arm). Exp1 outputs are out of
scope for v1 scoring; rows from Exp1 prompts must carry `prompt_not_asked`
annotations on the metrics listed in [Exp1 null policy](#exp1-null-policy).

**Source of truth:** `src/aedist/score_mechanical.py` implements this contract.
`experiments/prompts/articulation_matrix.md` documents which fields are
explicitly asked, implied, or absent in each prompt surface.

---

## Output schema — `experiments/derived/sota_cross_eval.csv`

Column order is deterministic. Numeric columns hold values rounded to 4 decimal
places, or empty string when null.

| Column | Type | Description |
|--------|------|-------------|
| `arm` | str | `naive` or `optimised` |
| `model` | str | Provider model ID |
| `run` | int (str in CSV) | Replication index (1-based) |
| `prompt_version` | str | Prompt family tag, e.g. `exp2` |
| `reference` | str | Release filename of the reference dataset the accuracy metrics were scored against, e.g. `vietnam_thermal_v1.csv` (ticket 0431) |
| `n_rows` | int (str in CSV) | Plant rows extracted from run output |
| `accuracy_coverage` | float\|null | Recall against reference |
| `accuracy_coverage_annotation` | str | Annotation code or empty |
| `accuracy_precision` | float\|null | Precision against reference |
| `accuracy_precision_annotation` | str | Same code as coverage (shared scorer) |
| `accuracy_f1` | float\|null | F1 = harmonic mean of coverage and precision |
| `accuracy_f1_annotation` | str | Same code as coverage |
| `accuracy_fuel` | float\|null | Fraction of matched rows with correct fuel |
| `accuracy_fuel_annotation` | str | Same code as coverage |
| `accuracy_status` | float\|null | Fraction of matched rows with correct status |
| `accuracy_status_annotation` | str | Same code as coverage |
| `accuracy_province` | float\|null | Fraction of matched rows with correct province |
| `accuracy_province_annotation` | str | Same code as coverage |
| `coherence_vocab_adherence` | float\|null | Fraction of rows with in-vocab fuel value |
| `coherence_vocab_adherence_annotation` | str | Annotation code or empty |
| `coherence_capacity_nonnegative` | float\|null | Fraction of rows with capacity ≥ 0 |
| `coherence_capacity_nonnegative_annotation` | str | Annotation code or empty |
| `provenance_source_presence` | float\|null | Fraction of rows with ≥1 source |
| `provenance_source_presence_annotation` | str | Annotation code or empty |
| `provenance_high_conf_dual_source` | float\|null | Fraction of HIGH-confidence rows with both sources |
| `provenance_high_conf_dual_source_annotation` | str | Annotation code or empty |
| `temporality_asof_presence` | float\|null | Fraction of rows with a status as-of date |
| `temporality_asof_presence_annotation` | str | Annotation code or empty |
| `temporality_plausible_range` | float\|null | Fraction of as-of dates in plausible range |
| `temporality_plausible_range_annotation` | str | Annotation code or empty |
| `field_completeness_core` | float\|null | Fraction of (row × core field) cells that are non-empty |
| `field_completeness_core_annotation` | str | Annotation code or empty |
| `field_completeness_capacity` | float\|null | Fraction of rows with a non-empty capacity value |
| `field_completeness_capacity_annotation` | str | Annotation code or empty |

---

## Per-metric definitions

### Accuracy (requires reference CSV)

All accuracy sub-metrics share a single annotation. When null, all six accuracy
columns carry the same annotation code.

**Numerator/denominator:**

- `accuracy_coverage` = TP / (TP + FN) — matched reference plants / all reference plants
- `accuracy_precision` = TP / (TP + FP) — matched reference plants / all system plants
- `accuracy_f1` = harmonic mean of coverage and precision
- `accuracy_fuel` = rows with correct fuel / matched rows
- `accuracy_status` = rows with correct status / matched rows
- `accuracy_province` = rows with correct province / matched rows

Matching uses the LP-based reconciler in `src/aedist/reconcile.py`.

**Null conditions:**

| Condition | Annotation |
|-----------|------------|
| `n_rows == 0` | `no_rows` |
| `--reference` path not provided or file missing | `reference_missing` |

**Known gap:** when `n_rows > 0` and reference is present but no rows reconcile
(all FP, 0 TP), `accuracy_fuel`, `accuracy_status`, and `accuracy_province` are
`None` with empty annotation — a scorer bug by this contract's own rule. It arises
because these sub-metrics share the top-level `accuracy.annotation` (which is
`None` on a successful scorer invocation) and their individual denominators
(matched rows) can be zero even when the scorer completes without error.

### Coherence

**`coherence_vocab_adherence`**

Numerator: rows where `fuel` (lowercased, stripped) is in the allowed set.  
Denominator: `n_rows`.

Allowed fuel vocabulary: `coal`, `gas`, `natural gas`, `local gas`,
`local natural gas`, `lng`, `imported lng`, `imported gas`, `oil`, `unknown`.

Null condition: `n_rows == 0` → annotation `no_rows`.

**`coherence_capacity_nonnegative`**

Numerator: rows where capacity (first non-empty of `capacity_mwe`, `total_mwe`,
`total_mw`, `capacity`) parses to a non-negative float.  
Denominator: `n_rows`.

A row with no capacity value (absent or empty) is NOT counted in the numerator —
it fails the same as a negative value. The metric measures "capacity is present
and non-negative" jointly, not "capacity is non-negative given it is present".

Null condition: `n_rows == 0` → annotation `no_rows`.

### Provenance

**`provenance_source_presence`**

Numerator: rows where `source_1` or `source_2` is non-empty.  
Denominator: `n_rows`.

Never null when rows are present (annotation always empty).

**`provenance_high_conf_dual_source`**

Numerator: rows where `confidence == "HIGH"` (case-insensitive) AND both
`source_1` and `source_2` are non-empty.  
Denominator: rows where `confidence == "HIGH"`.

**Null conditions:**

| Condition | Annotation |
|-----------|------------|
| No `confidence` key in any row | `column_missing` |
| `confidence` column present but no HIGH rows | `no_high_confidence` |

**Pipeline note:** `parse_and_canonicalize` always emits the full canonical
header set, inserting `""` for absent columns. For ingested rows, `confidence`
is therefore always present (possibly empty), so `column_missing` is unreachable
in the pipeline — the effective code when a model omitted the Confidence column
is `no_high_confidence` (zero HIGH rows → denominator 0 → null).

### Temporality

As-of date is resolved from the first non-empty of: `status_as_of`, `as_of`,
`date_as_of`, `freshness_date`.

**`temporality_asof_presence`**

Numerator: rows with a non-empty as-of cell.  
Denominator: `n_rows`.

**Null condition:** none of the as-of column aliases present in any row →
annotation `column_missing`.

**Pipeline note:** same as provenance above — `parse_and_canonicalize` always
inserts `status_as_of: ""` for runs that omitted the column. For ingested rows,
`column_missing` is unreachable; the effective path when the model omitted the
as-of column is `asof_presence = 0.0` (empty annotation) + `column_empty` on
`plausible_range`.

**`temporality_plausible_range`**

Numerator: rows whose as-of cell contains a year in `[1980, 2100]` (regex
`\b(19\d{2}|20\d{2}|2100)\b`).  
Denominator: rows with a non-empty as-of cell.

**Null conditions:**

| Condition | Annotation |
|-----------|------------|
| `column_missing` propagated from asof_presence | `column_missing` |
| As-of column present but all values empty | `column_empty` |

### Field completeness

Core fields: `name`, `fuel`, `status`, `cod`, `province` (5 columns).

**`field_completeness_core`**

Numerator: count of (row × core field) cells that are non-empty.  
Denominator: `n_rows × 5`.

**`field_completeness_capacity`**

Numerator: rows where capacity (same alias resolution as coherence) is non-empty.  
Denominator: `n_rows`.

**Null condition (both):** `n_rows == 0` → annotation `no_rows`.

---

## Annotation codes

| Code | Meaning |
|------|---------|
| `no_rows` | Extracted row list is empty; metric undefined |
| `reference_missing` | Reference CSV path was not provided or does not exist |
| `column_missing` | A required column is absent from all extracted rows |
| `no_high_confidence` | `confidence` column is present but no row has value `HIGH` |
| `column_empty` | Column is present but all cells are empty |
| `prompt_not_asked` | Prompt does not ask for this field; metric is excluded by articulation policy |

A null metric value with an empty annotation string is a scorer bug, not a
policy-sanctioned null — treat it as an error.

---

## Exp1 null policy

**Status: not yet implemented in v1 scorer.** The v1 scorer does not inspect
`prompt_version`. Exp1 rows currently receive `no_high_confidence` and
`column_empty` rather than `prompt_not_asked`. Implementation is deferred to v2.

**Intended behaviour (v2 target):** Exp1 prompt
(`experiments/prompts/modules/5_table.txt`) does not ask for `Confidence` or
`Status as-of-date`. The following metrics should be emitted as null with
`prompt_not_asked` annotation for any row with `prompt_version` beginning with
`exp1`:

- `provenance_high_conf_dual_source` — requires `Confidence` column
- `temporality_asof_presence` — requires `Status as-of-date` column
- `temporality_plausible_range` — requires `Status as-of-date` column

All other metrics are scoreable on Exp1 outputs (the remaining fields are
`asked_explicitly` in the Exp1 prompt surface — see `articulation_matrix.md`).

---

## Mart schema section

The Exp2 mart is a JSONL contract for analysis-time records. It is intentionally
smaller and more structured than the raw run artifacts: it carries stable
identifiers, nested summaries, and immutable artifact pointers, but it does not
carry verbatim chat payloads.

### Record kinds

- `run` records summarize one Exp2 run and point to the run JSON artifact.
- `probe` records summarize one turn/probe slice and point to the probe file.
- `score` records carry the mechanical-score payload for one run, the
	`reference` dataset the accuracy metrics were scored against, and point to
	the source run artifact.

#### Scorer columns intentionally outside the score-record payload (ticket 0386)

The "mechanical-score payload for one run" above is the *Exp2* payload, and it
is deliberately not a 1:1 image of every column `score_mechanical.py` can emit.
Three scorer columns (each with its `_annotation` sibling) are
**intentionally excluded** from the Exp2 mart's `score_summary`:

- `provenance_source_diversity` (+ `_annotation`)
- `provenance_source_spread` (+ `_annotation`)
- `temporality_cod_plausible` (+ `_annotation`)

These are Exp1 quality-spider metrics, not Exp2 mart fields. Their real chain
does not pass through the mart:

- `score_mechanical.py` computes them via `score_source_diversity`,
  `score_source_spread`, `score_cod_plausible` and writes them into
  `experiments/derived/sota_cross_eval.csv`.
- `score_exp1.py` recomputes them with the same `score_mechanical` helpers into
  its own `exp1_cross_eval.csv` cross-eval table.
- `plot_quality_spider_exp1.py` reads those columns *directly from the
  cross-eval CSV* to draw the Exp1 quality spider.

No mart consumer reads these three (audit in 0383/0386 found none), so wiring
them into `score_summary` would add schema surface with no reader. Per the
ratified Option B decision on ticket 0386, they stay out of scope: a lighter,
guarded omission rather than a `mart_schema_version` bump (the schema-extension
path that ticket 0431 can own if a mart consumer ever needs them). The
exclusion is encoded — not silently allowed — in `SCORER_OUT_OF_SCOPE` in
`tests/test_exp2_mart_contract.py`; a *new* unlisted scorer column still fails
the Layer-2 completeness check (ticket 0384).

### Versioning

- `mart_schema = "exp2_mart"`
- `mart_schema_version = 2`

Any change that adds, removes, or renames mart fields must bump the schema
version and ship a new validator model.

**v2 (ticket 0431):** `Exp2ScoreMartRecord` gains a top-level `reference`
field — the release filename of the dataset the accuracy metrics were
computed against (e.g. `vietnam_thermal_v1.csv`). It is `None` on legacy
score rows scored before the field was introduced. The reference is an
experimental condition: when a v2 reference is adopted (ticket 0413) the
tp/fp/fn change, and this field is what distinguishes pre- from
post-adoption rows. The `sota_cross_eval.csv` carries the same value in a
`reference` metadata column, and `build_exp2_mart_views.py` projects it
back into the score view.

**Design note — backfill vs omit-when-absent:** The mart and the
`measurements.jsonl` metrics dict use different migration strategies for
legacy rows, and both are intentional. The mart is a *completeness
snapshot*: committed mart rows were backfilled with the known default
(`vietnam_thermal_v1.csv`) so the mart is queryable without gaps.
`measurements.jsonl` is *append-only history*: `records_to_metrics()`
omits the `reference` key when it is `None`, following the 0139
precedent — legacy rows are preserved exactly as written and a missing
key is the faithful signal that the row predates the reference stamp.

### Artifact pointers

Each pointer field is a repo-relative path plus a SHA-256 digest of the target
file. The schema rejects absolute paths and upward traversal.

- `result_file`
- `parsed_table_file`
- `probe_file`

### Nested summaries

Mart records use grouped JSON summaries rather than a flat CSV-shaped record.
That keeps the mart readable for downstream code while leaving flattening to the
CSV view layer introduced in later tickets.

- Run records carry `run_summary`.
- Probe records carry `probe_summary`.
- Score records carry `score_summary`, grouped into accuracy, coherence,
	provenance, temporality, and field-completeness sections.

### Forbidden payloads

The mart schema uses strict field checking and must reject any verbatim chat
payload keys such as `raw_payload`, `messages`, `content`, or `thinking`.
Only structured summaries, hashes, and artifact pointers are allowed.

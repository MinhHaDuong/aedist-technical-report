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
| `run` | int | Replication index (1-based) |
| `prompt_version` | str | Prompt family tag, e.g. `exp2` |
| `n_rows` | int | Plant rows extracted from run output |
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

### Temporality

As-of date is resolved from the first non-empty of: `status_as_of`, `as_of`,
`date_as_of`, `freshness_date`.

**`temporality_asof_presence`**

Numerator: rows with a non-empty as-of cell.  
Denominator: `n_rows`.

**Null condition:** none of the as-of column aliases present in any row →
annotation `column_missing`.

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

Exp1 prompt (`experiments/prompts/modules/5_table.txt`) does not ask for
`Confidence` or `Status as-of-date`. The following metrics must be emitted as
null with `prompt_not_asked` annotation for any row with `prompt_version`
beginning with `exp1`:

- `provenance_high_conf_dual_source` — requires `Confidence` column
- `temporality_asof_presence` — requires `Status as-of-date` column
- `temporality_plausible_range` — requires `Status as-of-date` column

All other metrics are scoreable on Exp1 outputs (the remaining fields are
`asked_explicitly` in the Exp1 prompt surface — see `articulation_matrix.md`).

---

## Mart schema section

*(To be appended by ticket 0283 — Exp2 mart schema contract.)*

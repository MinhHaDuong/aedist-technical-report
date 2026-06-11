# Internal coherence as a zero-reference screen — exploratory analysis

Date: 2026-06-06 · Author conjecture, verified by Claude during the 0446 session.
Data: `experiments/derived/exp1_cross_eval.csv` + raw result tables
`experiments/outputs/exp1_batch2/*.csv` (14 models × 5 reps = 70 runs),
reference v2 (170 plants). Follow-up ticket: 0453.

## Conjecture (author)

Grading models on internal coherence criteria is enough to reject the weak
ones *without the reference list* — e.g. a run with no row variability in the
capacity, status, or status-as-of columns, or with implausible dates or
capacities, can be discarded on sight.

## What the quality spider actually computes

`plot_quality_spider_exp1.py` plots **10 separate axes** (5 dimensions × 2
indicators each); per model it shows the **median across the 5 reps with a
min–max band**. There is no composite score and no min-of-components
aggregation anywhere (the composite axis is open ticket 0201). The
"Cohérence" spider dimension is `accuracy_province` (valid Vietnamese
province) + `coherence_vocab_adherence` (fuel controlled vocabulary).

Reference-free indicators available in `exp1_cross_eval.csv`: fuel-vocab
adherence, capacity non-negativity, province validity, source presence /
diversity / spread, as-of presence, as-of year plausibility (1980–2100; the
all-identical-year → 0 rule described here was removed by ticket 0505), COD
plausibility, field completeness.
`coherence.py` (row / dedup / control-total checks) does **not** feed the
cross-eval CSV. **Not implemented anywhere: within-run variability of the
capacity or status columns** — the conjecture's criterion.

## Findings

### 1. The conjecture holds — via the variability criterion

Per run, count distinct non-empty values in the capacity and status columns
of the raw result table:

- **Spearman(cap_distinct, accuracy_f1) = 0.904** across the 70 runs
  (status_distinct: 0.677).
- **Not an output-length artifact.** cap_distinct is bounded by the row
  count n, and n itself tracks F1 (Spearman 0.47), so the pooled correlation
  could mix "many rows" with "varied rows". It does not: the partial Spearman
  of cap_distinct vs F1 controlling for n is **0.887**, and the fixed-n
  contrast is decisive — gpt-oss-20b and gpt-5.5 both emit ~84 rows (medians
  83 vs 85) with cap_distinct 1 vs 37 and F1 0.000 vs 0.611. The normalized
  ratio cap_distinct/n alone scores 0.643.
- Rule `cap_distinct ≤ 4 OR status_distinct ≤ 1`: rejects **23 runs with no
  false rejection in-sample** (no run with F1 ≥ 0.25 is rejected). Caveat:
  the cutoffs were tuned on the same 70 runs they are scored against — this
  is an existence proof, not a validated detector; 0453 should hold out data
  (e.g. fit on 3 reps, test on 2, or validate on Exp2/Exp3 outputs). 3 weak
  escapes sit just above threshold (cap_distinct 5–6, F1 0.10–0.20):
  qwen3.6-flash r2 r3, gpt-oss-120b r2.
- Model-level medians separate the weak five **exactly** and with a wide
  margin: claude-haiku-4.5, gpt-oss-120b, gpt-oss-20b, qwen3.6-flash,
  qwen3.6-35b-a3b have median cap_distinct **1–4**; the strong nine have
  **11–37**.
- The rule also catches **deepseek-v4-flash run 5** (17 rows, F1 0.022) — a
  degenerate run from an otherwise strong model, invisible to model-level
  exclusion. The screen works at run granularity.

Illustration — `gpt-oss-20b-run4.csv` is 100 rows of pure template
fabrication: invented sequential names (Trung Nam 1/2/3, …), every row
600.0 MW / "Operating" / sequential CODs / dual fake sources / confidence
HIGH. `qwen3.6-flash-run5.csv`: 496 rows, every one 1200.0 MW and
"Operating" (verified).

### 2. The currently computed indicators do NOT suffice

- `coherence_vocab_adherence` is **inverted**: gpt-oss-20b scores a perfect
  1.00 (fabricated rows use impeccable vocabulary); claude-opus-4.6 scores
  0.83. Same for province validity and field completeness (saturated).
- `capacity_nonnegative` is 1.0 for every run — no signal.
- Source diversity/spread catch 4 of the 5 weak models (≤ 0.15 vs ≥ 0.40)
  but **gpt-oss-120b escapes** (diversity 1.0, spread 0.83: internally
  beautiful fabrication).
- Date plausibility carries no signal (weak models score 1.0; strong models
  could score 0.0 through the all-identical-year annotation rule — see below;
  that rule was removed by ticket 0505).

### 3. One conjecture component must be rejected

**Status-as-of variability is not a valid criterion**: constant as-of is the
norm in strong runs too — claude-sonnet-4.6 stamps the run date on every row
(median asof_distinct = 1). This is also why its
`temporality_plausible_range` read 0.0 at the time of this analysis: an
annotation rule (`all_identical`), not a failure — ticket 0505 has since
removed that rule, so a uniform plausible as-of year now scores normally. A
variability requirement on as-of would falsely reject top models.

## Design implication — two-level scoring (author, 2026-06-06)

1. **Run-level screen** (information credibility): within-run capacity /
   status variability thresholds reject degenerate outputs with no reference.
2. **Model-level reliability grade** (source reliability): aggregate the
   screen across the 5 repetitions; a model version with 5/5 incoherent runs
   is disqualified as a source altogether.

In the NATO STANAG 2511 ("Admiralty") vocabulary: level 1 rates *information
credibility*, level 2 rates *source reliability*. Wiring these as scorer
columns (score_mechanical + metrics dict, ADR-7) is ticket 0453.

## Reproduction

```python
import csv, glob, json, re
import pandas as pd

rows = []
for rec_path in sorted(glob.glob("experiments/outputs/exp1_batch2/*.record.json")):
    rec = json.load(open(rec_path))
    table = list(csv.DictReader(open(rec["result_file"], encoding="utf-8")))
    def distinct(cands):
        vals = [r[c].strip() for r in table for c in cands
                if c in r and (r[c] or "").strip()]
        return len(set(vals))
    rows.append(dict(
        model=rec["method_params"]["model"].split("/")[-1],
        run=int(re.search(r"run(\d+)", rec_path).group(1)),
        cap_d=distinct(["capacity_mwe", "capacity_mw", "total_mwe", "capacity"]),
        st_d=distinct(["status"])))
var = pd.DataFrame(rows)
ce = pd.read_csv("experiments/derived/exp1_cross_eval.csv")
ce["model"] = ce["model"].str.split("/").str[-1]
m = var.merge(ce[["model", "run", "accuracy_f1"]], on=["model", "run"])
print(m["cap_d"].corr(m["accuracy_f1"], method="spearman"))   # 0.904
m["reject"] = (m.cap_d <= 4) | (m.st_d <= 1)
print(pd.crosstab(m.reject, m.accuracy_f1 < 0.25))            # 23 TP, 0 FP, 3 FN
```

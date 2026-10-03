VERDICT: DONE

Ticket 0338 — Définir constantes figsize standards Beamer dans aedist.util

### Changes
1. **`src/aedist/util.py`** — Added 11 figsize constants:
   - Core: `SLIDE_FIGSIZE_FULL`, `SLIDE_FIGSIZE_WIDE`, `SLIDE_FIGSIZE_HALF`, `SLIDE_FIGSIZE_POLAR_2x2`
   - Extended: `SLIDE_FIGSIZE_2PANEL`, `SLIDE_FIGSIZE_HEATMAP`, `SLIDE_FIGSIZE_MATRIX`, `SLIDE_FIGSIZE_SPIDER`, `SLIDE_FIGSIZE_TIMELINE`, `SLIDE_FIGSIZE_SCATTER`, `SLIDE_FIGSIZE_DAG`, `SLIDE_FIGSIZE_STRIP`, `SLIDE_FIGSIZE_PLACEHOLDER`, `SLIDE_FIGSIZE_BASE_VS_CENSUS`

2. **12 plot scripts refactored** to use constants instead of hardcoded tuples:
   - `plot_ablation.py` (3 uses)
   - `plot_base_vs_census.py` (2 uses)
   - `plot_capability_dag.py` (1 use)
   - `plot_capability_timeline.py` (1 use)
   - `plot_cost_quality.py` (1 use)
   - `plot_exp2_arms_comparison.py` (1 use)
   - `plot_exp2_coverage_certainty.py` (1 use)
   - `plot_exp2_turn_trajectory.py` (2 uses)
   - `plot_quality_spider.py` (1 use)
   - `plot_quality_spider_exp1.py` (1 use)
   - `plot_regimes_scatter.py` (1 use)
   - `plot_scaling_curve.py` (1 use)

3. **`tests/test_no_hardcoded_figsize.py`** — Adherence test that detects hardcoded `figsize=(...)` tuples in plot scripts.

### Verification
- `make check-fast` passes (1675 tests, 0 failures)
- Ruff lint passes
- Adherence test passes

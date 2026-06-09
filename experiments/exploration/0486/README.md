# 0486 source-concordance prototypes

Throwaway exploration scripts that produced the **light-reviewed** numbers quoted
in tickets 0486 and 0494. The raid is expected to *productionise* these into a
Makefile-wired `src/aedist/` script; they live here so the numbers are
reproducible in the meantime.

Run from the **repo root** (they use repo-root-relative paths + `aedist.config`):

```bash
uv run python experiments/exploration/0486/explore_bars.py       # aggregate bars: Wikipedia 90, GEM 120 (raw)
uv run python experiments/exploration/0486/explore_review.py     # ASCII-fold review: GEM 88%, Wikipedia 73%
uv run python experiments/exploration/0486/explore_superset.py   # GEM 153 rows/119 distinct; 11 true GEM-only
```

Inputs (all tracked):
- `data/reference/vietnam_thermal_plants_v2_classified.csv` — the reference
- `data/reference/gem_thermal.csv` — GEM
- `data/reference/raw/wikipedia_coal_vietnam-2026-06-09.wikitext` + `wikipedia_power_vietnam-2026-06-09.wikitext`
  — Wikipedia (coal list + general page's `==Gas turbines==` section; raw wikitext, `?action=raw`)

Caveats (carried into the tickets): the ASCII-fold recovery slightly over-counts via
grain mismatch (one source row ↔ several reference phases), so 88%/73% are upper-ish.
The full per-plant HITL concordance is post-arXiv (ticket 0498).

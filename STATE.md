Last updated: 2026-04-03

## Status

Pipeline end-to-end via Makefile. Census done (33 models, F1 2–66%, $0.73). 140 tests pass. experiments/scripts/ folded into src/aedist (#66–#70). MASTERPLAN written (#72). Sweep 2 ready to launch.

## Next actions

1. Launch Sweep 2: `cd experiments && make sweep2` — 5 models × 3 regimes × 3 runs (#10)
2. Cost data for Pareto chart (#59)
3. Tabulate relances and comparaison after Sweep 2 (#47, #48)
4. Reframe slides: methods not models

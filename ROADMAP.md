## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Monorepo with 140 tests
- [x] Census: 33 models, F1 2-66%, $0.73
- [x] Per-table pipeline: one script, one output, Make orchestrates (#43)
- [x] Slides read from generated CSVs (PR #40)
- [x] select_sweep2 computes model selection (PR #60)
- [x] Fold experiments/scripts/ into src/aedist (#66, PR #70)
- [ ] Run Sweep 2: information regimes (#10)
- [ ] Cost data in Pareto chart (#59)
- [ ] Tabulate relances and comparaison (#47, #48)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Chunked RAG strategy (currently only wholesale)
- Reasoning effort sweep (#11) — needs reasoning models on Padme
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors

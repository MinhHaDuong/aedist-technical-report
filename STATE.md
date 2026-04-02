Last updated: 2026-04-02

## Status

Pipeline end-to-end: `make sweep1-summary && make select && make tables && make figures && make report && make slides`. Census done (33 models incl. Mistral Large, F1 2-66%, $0.73). 116 tests pass. Top 5 cloud models selected for Sweep 2. Sweep 2 ready to launch.

## Blockers

- Sweep 2 scripts (query_multiturn, query_rag, query_web) only talk to OpenRouter — local Padme models excluded from sweep 2 for now.

## Next actions

1. Launch Sweep 2: `cd experiments && make sweep2` — 5 models × 3 modes × 3 runs (#10)
2. Cost data for Pareto chart (#59)
3. Tabulate relances and comparaison after Sweep 2 (#47, #48)
4. Pipeline UX: progress bars, checkpointing (#22)

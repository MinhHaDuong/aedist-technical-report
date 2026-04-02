Last updated: 2026-04-02

## Status

End-to-end pipeline works: `make sweep1-summary && make select && make tables && make figures && make report && make slides`. Census done (32 models, F1 2-66%, $0.73). 109 tests pass.

## Blockers

None

## Next actions

1. Run `make select` then Sweep 2 (#10)
2. Pipeline UX: progress bars, checkpointing (#22)
3. Cost data for Pareto chart (#59)
4. Tabulate relances and comparaison after Sweep 2 (#47, #48)

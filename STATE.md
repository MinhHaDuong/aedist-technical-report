Last updated: 2026-04-02

## Status

Pipeline redesign complete. One script per table/figure, Makefile orchestrates. convert.py deleted. Census evaluated (32 models, F1 2-66%). Ready for Sweep 2.

## Blockers

None

## Next actions

1. Select top models: `make select` (#20)
2. Pipeline UX: progress bars, checkpointing (#22)
3. Run Sweep 2: information regimes (#10)
4. Beamer slides with generated chart data (#15, #40)

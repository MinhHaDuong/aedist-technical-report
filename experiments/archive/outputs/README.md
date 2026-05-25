# Experiment outputs — archive

This directory stores historical output datasets moved out of active discovery.

## Scope

- Keep here: retired runs, exploratory sweeps, and smoke/probe artifacts.
- Keep out of here: datasets required by current report/manuscript rebuilds.

## Why this split exists

The active outputs tree (experiments/outputs/) is scanned during measurements
rebuild. Archived datasets are moved under experiments/archive/outputs/ to keep
active discovery focused and to avoid accidental inclusion of smoke/probe runs.

## Typical archived groups

- Historical ablation and regime directories
- Exp2 historical batches and protocol review outputs
- Smoke and probe directories (for example sota_exp2_smoke, sota_smoke, and
  Exp3/Qwen smoke arms)

## Notes

- Archive data remains versioned and reproducible; it is only de-scoped from
  default rebuild discovery.
- If an archived dataset needs to re-enter active analysis, move it back into
  experiments/outputs/ in a dedicated change.

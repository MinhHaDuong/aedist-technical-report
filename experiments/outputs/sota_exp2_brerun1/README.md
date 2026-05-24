# Exp 2 Optimized Arm — Phase B Full Batch, Corrected Classifier (brerun1)

Run date: 2026-05-23

## Why This Folder Exists

This batch replaces `sota_exp2_phase_b_full/` as the canonical Phase B production data for
the optimized arm. It was created after a classifier audit (ticket 0243) revealed that the
classifier used in `sota_exp2_phase_b_full/` was `nvidia/nemotron-nano-9b-v2` at 8K chars,
which produced routing errors on two boundary cases:

- **False positive**: PRELIMINARY ROSTER turns (candidate universe with explicit "I will not
  produce the final inventory yet") were classified as `report`, causing premature VERIFY turns.
- **False negative**: Polished 18.7K-char inventories were classified as `no_report` (truncated
  at 8K, hiding the inventory table), causing unnecessary ENCOURAGE turns.

The corrected classifier is `deepseek/deepseek-v4-pro` at 16K chars (PR #451, ticket 0243).
A hand audit confirmed all 60 classifier decisions in this batch used the corrected model.

Phase A designs are reused from `sota_exp2_phase_b0/probes/{agent}_run01/` (same as the
prior batch), so variance across reps measures Phase B reproducibility only.

## Model Set

| Agent | Model |
|-------|-------|
| anthropic | `claude-opus-4-6` |
| openai | `gpt-5.5-2026-04-23` |
| mistral | `mistral-large-2512` |
| qwen | `qwen3-max-2026-01-23` |

## Per-Run Results

Note: the `Rows` values recorded in this README reflect the batch-time
`inventory_rows` heuristic stored in per-run JSON metadata on 2026-05-23.
Ticket 0277 later tightened the canonical definition to mean plant-table rows
only, excluding summary tables. Use regenerated downstream artifacts such as
`report/inputs/generated/tab_exp2_arms_runs.csv` for the corrected canonical
counts; treat the table below as historical run-log output.

| Agent | Run | Turns | Class trace | Rows | Cost |
|-------|----:|------:|-------------|-----:|-----:|
| anthropic | 1 | 3 | no_report→report→report | 117 | $1.780 |
| anthropic | 2 | 3 | no_report→report→report | 123 | $1.905 |
| anthropic | 3 | 3 | no_report→report→report | 135 | $2.043 |
| anthropic | 4 | 3 | no_report→report→report | 158 | $1.803 |
| anthropic | 5 | 3 | no_report→report→report | 141 | $2.090 |
| mistral | 1 | 4 | no_report→no_report→no_report→report | 22 | $0.393 |
| mistral | 2 | 4 | no_report→no_report→no_report→report | 19 | $0.479 |
| mistral | 3 | 4 | no_report→no_report→report→report | 15 | $0.572 |
| mistral | 4 | 4 | no_report→no_report→no_report→report | 27 | $0.482 |
| mistral | 5 | 3 | no_report→report→report | 25 | $0.355 |
| openai | 1 | 4 | no_report→no_report→report→report | 122 | $1.141 |
| openai | 2 | 3 | no_report→report→report | 159 | $0.910 |
| openai | 3 | 3 | no_report→report→report | 174 | $0.923 |
| openai | 4 | 3 | no_report→report→report | 99 | $0.883 |
| openai | 5 | 3 | no_report→report→report | 209 | $0.982 |
| qwen | 1 | 2 | report→report | 13 | $0.162 |
| qwen | 2 | 2 | report→report | 17 | $0.161 |
| qwen | 3 | 2 | report→report | 18 | $0.170 |
| qwen | 4 | 2 | report→report | 17 | $0.170 |
| qwen | 5 | 2 | report→report | 18 | $0.172 |

**Total cost: $17.58** (20 runs, all classification=report)

## How It Was Run

```bash
# Per wave (N=1..5), 4 agents in parallel:
uv run python -m experiments.sota.exp2_interactive_smoke \
    --agents anthropic openai mistral qwen \
    --run-number N \
    --output-dir experiments/outputs/sota_exp2_brerun1 \
    --reuse-phase-a-from experiments/outputs/sota_exp2_phase_b0/probes \
    --no-confirm

# Consolidation per rep:
uv run python -m experiments.sota.exp2_phase_b0_consolidate \
    --phase-b0-dir experiments/outputs/sota_exp2_brerun1 \
    --run-number N
```

Classifier: `deepseek/deepseek-v4-pro`, 16K char excerpt, max_tokens=1024.

## File Layout

- `{agent}_runNN.json` — run metadata (cost, turns, classification, inventory_rows)
- `{agent}_runNN.md` — inventory narrative from the final `report`-classified turn
- `{agent}_runNN.raw.json` — raw provider response for that turn
- `summary.json` — machine-readable array of all 20 per-run records
- `probes/` — per-turn artefacts (`.record.json`, `.classification.json`, `.cost.json`, etc.)

Historical note: the `inventory_rows` field stored in these existing JSON files
predates the plant-table-only fix from 0277 and may include summary tables.

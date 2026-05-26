# arm4 (5D) run01 — qwen rerun on the correct model

**Re-run 2026-05-26 on `qwen3.7-max-2026-05-20` (DashScope direct).**

The original arm4 run01 qwen output ran on the superseded model
`qwen3-max-2026-01-23` (original sweep, 2026-05-23) and is archived at
`experiments/archive/outputs/sota_exp3_arm4_batch1_run01_qwen_oldmodel/` with its
own README. This directory is the verified replacement on the correct model, so
the qwen arm4 cell is now uniformly `qwen3.7-max-2026-05-20` across all five reps.

Rerun command (from `experiments/`):

```
PYTHONPATH=.. uv run --project .. --env-file ../.env \
  python sota/exp2_interactive_smoke.py \
  --agents qwen \
  --output-dir outputs/sota_exp3_arm4_qwen_rerun/run01 \
  --evidence-pack-manifest evidence_packs/all18tables.yaml --no-confirm
```

Run record: status `pass`, 2 turns, $0.69, produced a full inventory table
(verified before absorption).

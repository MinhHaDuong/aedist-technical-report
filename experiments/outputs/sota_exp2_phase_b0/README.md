# Exp 2 Optimized Arm — Phase B-0 Gate

Run date: 2026-05-23

## Per-agent results

| Agent | Model | Classification | Turns | Total cost | Inventory rows |
|-------|-------|---------------|------:|-----------:|---------------:|
| openai | gpt-5.5-2026-04-23 | report | 4 | $0.9502 | 156 |
| qwen | qwen3-max-2026-01-23 | report | 3 | $0.2493 | 31 |
| mistral | mistral-large-2512 | report | 2 | $0.2938 | 50 |
| anthropic | claude-opus-4-6 | report | 2 | $1.2293 | 120 |

**Total cost:** $2.7225

## Classifier note

OpenAI and Qwen runs (first attempt, 2026-05-22) had a broken classifier:
`OPENROUTER_API_KEY` was absent from the subprocess environment.
Turns 1–3 (openai) and 1–2 (qwen) returned `no_report` with `classifier_cost_usd=0.0`.
The classifier was re-run on the final turns (2026-05-23) and returned `report` for both.

Mistral and Anthropic re-runs (second attempt, 2026-05-23) used `uv run`
so the classifier fired correctly on all turns.

## Gating verdict

Probe audit files in `probes/`:
- `summary_20260522T2354Z_openai_qwen.md`
- `summary_20260523T1026Z_anthropic.md`

## File layout

- `{agent}_run01.md` — inventory narrative from final report turn
- `{agent}_run01.json` — per-run metadata record
- `{agent}_run01.raw.json` — raw provider response (final report turn)
- `summary.json` — machine-readable array of per-agent records
- `probes/` — per-turn debug artefacts and earlier audit files

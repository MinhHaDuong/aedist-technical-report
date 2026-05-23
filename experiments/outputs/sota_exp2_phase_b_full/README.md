# Exp 2 Optimized Arm — Phase B-0 Gate

Run date: 2026-05-23

## Per-agent results

| Agent | Model | Classification | Turns | Total cost | Inventory rows |
|-------|-------|---------------|------:|-----------:|---------------:|
| anthropic | claude-opus-4-6 | report | 2 | $1.2293 | 120 |
| mistral | mistral-large-2512 | report | 2 | $0.2938 | 50 |
| openai | gpt-5.5-2026-04-23 | report | 4 | $0.9502 | 156 |
| qwen | qwen3-max-2026-01-23 | report | 3 | $0.2493 | 31 |
| anthropic | claude-opus-4-6 | report | 2 | $1.3018 | 111 |
| mistral | mistral-large-2512 | report | 3 | $0.4358 | 27 |
| openai | gpt-5.5-2026-04-23 | report | 2 | $0.4750 | 112 |
| qwen | qwen3-max-2026-01-23 | report | 3 | $0.1430 | 18 |
| anthropic | claude-opus-4-6 | report | 2 | $1.4082 | 26 |
| mistral | mistral-large-2512 | report | 2 | $0.3665 | 38 |
| openai | gpt-5.5-2026-04-23 | report | 2 | $0.5422 | 121 |
| qwen | qwen3-max-2026-01-23 | report | 2 | $0.1678 | 18 |
| anthropic | claude-opus-4-6 | report | 2 | $1.3089 | 86 |
| mistral | mistral-large-2512 | report | 2 | $0.3142 | 36 |
| openai | gpt-5.5-2026-04-23 | report | 3 | $0.9158 | 139 |
| qwen | qwen3-max-2026-01-23 | report | 2 | $0.1908 | 29 |
| anthropic | claude-opus-4-6 | report | 2 | $1.2995 | 2 |
| mistral | mistral-large-2512 | report | 3 | $0.5176 | 34 |
| openai | gpt-5.5-2026-04-23 | report | 2 | $0.3996 | 106 |
| qwen | qwen3-max-2026-01-23 | report | 2 | $0.1854 | 19 |

**Total cost:** $12.6947

## Classifier note

OpenAI and Qwen runs (first attempt, 2026-05-22) had a broken classifier:
`OPENROUTER_API_KEY` was absent from the subprocess environment.
Turns 1–3 (openai) and 1–2 (qwen) returned `no_report` with `classifier_cost_usd=0.0`.
The classifier was re-run on the final turns (2026-05-23) and returned `report` for both.

Mistral and Anthropic re-runs (second attempt, 2026-05-23) used `uv run`
so the classifier fired correctly on all turns.

## Gating verdict

Probe audit files in `probes/`:
- `summary_20260523T1029Z_mistral.md`
- `summary_20260523T1030Z_openai.md`
- `summary_20260523T1033Z_anthropic.md`
- `summary_20260523T1038Z_qwen.md`
- `summary_20260523T1043Z_mistral.md`
- `summary_20260523T1049Z_mistral.md`
- `summary_20260523T1049Z_openai.md`
- `summary_20260523T1054Z_qwen.md`
- `summary_20260523T1055Z_anthropic.md`
- `summary_20260523T1100Z_openai.md`
- `summary_20260523T1103Z_mistral.md`
- `summary_20260523T1107Z_openai.md`
- `summary_20260523T1108Z_anthropic.md`
- `summary_20260523T1109Z_qwen.md`
- `summary_20260523T1116Z_mistral.md`
- `summary_20260523T1116Z_openai.md`
- `summary_20260523T1121Z_anthropic.md`
- `summary_20260523T1121Z_qwen.md`

## File layout

- `{agent}_run01.md` — inventory narrative from final report turn
- `{agent}_run01.json` — per-run metadata record
- `{agent}_run01.raw.json` — raw provider response (final report turn)
- `summary.json` — machine-readable array of per-agent records
- `probes/` — per-turn debug artefacts and earlier audit files

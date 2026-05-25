# WEAK CLASSIFIER -- DO NOT USE
# SOTA Exp2 Optimized Arm — Phase B Full Batch (N=5)

## What This Folder Is

This folder contains outputs for the **optimized arm** of Experiment 2 in the AEDIST Vietnam thermal-plant extraction study.

Context for a first-time reader:

- Task: produce a structured inventory of Vietnam thermal generation assets (focus on plants above 30 MWe) using an interactive Phase A/B protocol.
- Experimental role: this is the treatment/optimized condition, contrasted against the naive single-shot arm in `sota_exp2_naive_arm/`.
- Unit of analysis: one multi-turn session per replication (`rep#`) with run metadata (`cost_usd`, `wall_s`, classifier label, turns, inventory_rows).
- Scope here: production runs for four frontier agents (5 reps each, 20 total).

The production model set in this folder is:

- `anthropic` → `claude-opus-4-6`
- `openai` → `gpt-5.5-2026-04-23`
- `mistral` → `mistral-large-2512`
- `qwen` → `qwen3-max-2026-01-23`

Optimized arm means a two-phase interactive protocol: Phase A generates a research strategy (web-search-assisted), Phase B executes it in a multi-turn loop until the dialogue classifier returns `report`.

## Why This Exists

This batch provides the N=5 reproducibility replication for the optimized arm to pair against the naive arm. Rep 1 served double duty as the Phase B-0 gate (confirming the protocol produces a `report` before committing to the full batch). Reps 2–5 reuse the same Phase A design from rep 1 — only Phase B is re-executed — so variance across reps measures Phase B reproducibility, not Phase A variability.

## How It Was Run

- Script: `python -m experiments.sota.exp2_interactive_smoke`
- Key flags: `--reuse-phase-a-from experiments/outputs/sota_exp2_phase_b0/probes --run-number N --no-confirm`
- Consolidation per rep: `python -m experiments.sota.exp2_phase_b0_consolidate --run-number N`
- Phase A design source: `experiments/outputs/sota_exp2_phase_b0/probes/{agent}_run01/`
- Replications: N=5 per agent; rep 1 = Phase B-0 gate run (committed separately in `sota_exp2_phase_b0/`)
- Parallelism: 4 agents in parallel per rep (one process per agent, each hitting a different provider)
- Output summary source of truth: `summary.json`

Per production run, artifacts are flattened at top level as a 3-file set:

- `<agent>_runNN.json` → run metadata (cost/runtime/classification/turns)
- `<agent>_runNN.md` → narrative/report text from the final `report`-classified turn
- `<agent>_runNN.raw.json` → raw provider payload for that turn

## When It Ran

- Rep 1 (Phase B-0 gate): `2026-05-23` morning — OpenAI and Qwen first attempt from prior day failed classifier; re-classified same day. Mistral and Anthropic re-run `2026-05-23`.
- Reps 2–4: `2026-05-23`, approximately 12:27–13:10 UTC.
- Rep 5: `2026-05-23`, approximately 13:14–13:22 UTC.

Overall production window: `2026-05-23T10:25Z` to `2026-05-23T13:22Z`.

## Who Uses This

Humans:

- Quick QA on cost, runtime, turns, and inventory_rows per rep
- Cross-agent and optimized-vs-naive comparison before downstream evaluation

Bots:

- Machine-readable per-run metadata from `summary.json`
- Deterministic path structure for run artifacts (`*_runNN.json`, `*_runNN.md`, `*_runNN.raw.json`)

## Metric Definitions

- `classification`: `report` / `no_report` from the dialogue classifier applied to each Phase B turn; final classification uses the last turn classified `report`
- `turns`: number of Phase B turns executed (`designed_prompt` turn + up to N `verify` turns)
- `class_trace`: per-turn classification sequence, e.g. `report→no_report` (turn 1 = report, turn 2 = no_report on verify)
- `inventory_rows`: heuristic count of markdown table data rows in the final `report` narrative
- `total_cost_usd`: phase_a_cost (0.0 for reps 2–5, already counted in rep 1) + phase_b_cost + classifier_cost

## Run Table

| agent | model | rep# | cost_usd | wall_s | turns | class_trace | inventory_rows |
|---|---|---:|---:|---:|---:|---|---:|
| anthropic | claude-opus-4-6 | 1 | 1.2293 | 378.6 | 2 | report→report | 120 |
| anthropic | claude-opus-4-6 | 2 | 1.3018 | 436.7 | 2 | report→report | 111 |
| anthropic | claude-opus-4-6 | 3 | 1.4082 | 501.9 | 2 | report→report | 26 |
| anthropic | claude-opus-4-6 | 4 | 1.3089 | 434.7 | 2 | report→no_report | 86 |
| anthropic | claude-opus-4-6 | 5 | 1.2995 | 459.1 | 2 | report→report | 2 |
| mistral | mistral-large-2512 | 1 | 0.2938 | 159.8 | 2 | report→report | 50 |
| mistral | mistral-large-2512 | 2 | 0.4358 | 214.3 | 3 | no_report→report→report | 27 |
| mistral | mistral-large-2512 | 3 | 0.3665 | 148.9 | 2 | report→report | 38 |
| mistral | mistral-large-2512 | 4 | 0.3142 | 119.8 | 2 | report→report | 36 |
| mistral | mistral-large-2512 | 5 | 0.5176 | 201.4 | 3 | no_report→report→report | 34 |
| openai | gpt-5.5-2026-04-23 | 1 | 0.9502 | 451.2 | 4 | no_report→no_report→no_report→report | 156 |
| openai | gpt-5.5-2026-04-23 | 2 | 0.4750 | 234.3 | 2 | report→report | 112 |
| openai | gpt-5.5-2026-04-23 | 3 | 0.5422 | 262.7 | 2 | report→report | 121 |
| openai | gpt-5.5-2026-04-23 | 4 | 0.9158 | 357.1 | 3 | no_report→report→report | 139 |
| openai | gpt-5.5-2026-04-23 | 5 | 0.3996 | 179.3 | 2 | report→report | 106 |
| qwen | qwen3-max-2026-01-23 | 1 | 0.2493 | 621.9 | 3 | no_report→no_report→report | 31 |
| qwen | qwen3-max-2026-01-23 | 2 | 0.1430 | 700.6 | 3 | no_report→report→report | 18 |
| qwen | qwen3-max-2026-01-23 | 3 | 0.1678 | 409.9 | 2 | report→report | 18 |
| qwen | qwen3-max-2026-01-23 | 4 | 0.1908 | 532.8 | 2 | report→report | 29 |
| qwen | qwen3-max-2026-01-23 | 5 | 0.1854 | 494.9 | 2 | report→report | 19 |

## Summary Analysis

Headline:

- Total production runs: `20`
- Total cost: `$12.6947`
- Runs classified `report`: `20/20`

By agent:

- `claude-opus-4-6`: `5/5` report, consistently 2 turns; highest cost (mean `$1.31`, range `$1.23–$1.41`) and moderate wall time (mean `442s`). Wide inventory_rows variance (2–120), suggesting output length is highly stochastic across reps.
- `gpt-5.5-2026-04-23`: `5/5` report, 2–4 turns; moderate cost (mean `$0.66`), best inventory_rows yield (mean `127`, range `106–156`). Rep 1 required 4 turns due to broken classifier (see Research Notes).
- `mistral-large-2512`: `5/5` report, 2–3 turns; lowest cost after Qwen (mean `$0.39`), fastest wall time (mean `169s`). Two reps (2 and 5) needed an extra turn after an initial `no_report`.
- `qwen3-max-2026-01-23`: `5/5` report, 2–3 turns; lowest cost (mean `$0.19`), but longest wall time (mean `552s`) due to extended reasoning. Lowest inventory_rows yield (mean `23`, range `18–31`).

Caveats:

- `inventory_rows` is a heuristic markdown table row count from the final `report` narrative, not an adjudicated quality metric.
- `wall_s` is the sum of Phase B turn wall times; Phase A wall time (not repeated for reps 2–5) is excluded.
- Final scientific claims should use the project evaluation pipeline, not this README-only triage layer.

## Research Notes

- **OpenAI rep 1 four-turn trace**: `class_trace = no_report→no_report→no_report→report`. Turns 1–3 had `classifier_cost_usd=0.0` because `OPENROUTER_API_KEY` was absent from the Phase B-0 subprocess environment. The final turn was re-classified manually using the correct key and returned `report`. The `no_report` entries in the trace are classifier-env failures, not model failures.
- **Qwen rep 1 three-turn trace**: same root cause — turns 1–2 returned `no_report` with `classifier_cost_usd=0.0`. Re-classified on turn 3.
- **Null-content glitch (Mistral rep 2, OpenAI rep 4)**: two verify turns returned `finish_reason: None` with `content_len=0` but non-zero reasoning tokens. The failed run directory was moved and the run retried; both recovered on the first retry. This is an intermittent provider-side issue with no harness-level workaround.
- **Mistral API format change**: between reps 1 and 2, `outputs[0].content` in the Mistral Agents API response changed from `list[{type, text}]` to a bare `str`. Fixed in `exp2_phase_b0_consolidate.py` with an `isinstance(content, str)` guard.
- **`summary.json` consistency fix**: rep 1 entries were initially populated with rep 2 values due to a run-number stamping bug in `_process_agent()` (always returned `"run": 1`). Corrected in the rep 4 commit by rebuilding all 20 rows from the authoritative flat `agent_runNN.json` files.
- **429-retry not implemented**: the ticket exit criteria listed adding rate-limit retry to OpenAI and Qwen adapters. Not implemented because the 1-agent-per-process parallelism strategy means no two agents share a provider simultaneously. No 429 errors occurred across all 20 runs.
- **Reproducibility anchor**: use `summary.json` in this folder as the canonical machine-readable record for this run set.

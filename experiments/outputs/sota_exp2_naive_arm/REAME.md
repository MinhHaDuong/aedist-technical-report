# SOTA Exp2 Naive Arm

## What This Folder Is

This folder contains outputs for the **naive arm** of Experiment 2 in the AEDIST Vietnam thermal-plant extraction study.

Context for a first-time reader:

- Task: produce a structured inventory of Vietnam thermal generation assets (focus on plants above 30 MWe) from a single prompt.
- Experimental role: this is the null/comparator condition against the optimized interactive Exp2 protocol.
- Unit of analysis: one model response per replication (`rep#`) with run metadata (`cost_usd`, `wall_s`, classifier label, and derived heuristics).
- Scope here: production runs only for four frontier agents (5 reps each, 20 total), plus preserved probe snapshots for provenance.

The production model set in this folder is:

- `anthropic` -> `claude-opus-4-6`
- `openai` -> `gpt-5.5`
- `mistral` -> `mistral-large-2512`
- `qwen` -> `qwen3-max-2026-01-23`

Naive arm means single-shot prompting (no iterative protocol loop), then post-hoc classification.

## Why This Exists

This arm is the null/comparator baseline against the optimized Exp2 interactive protocol. It estimates what each agent can deliver from one direct prompt without the Phase A/B scaffolding.

## How It Was Run

- Prompt source: `experiments/sota/protocol_07_naive_prompt.md`
- Script: `python -m experiments.sota.exp2_naive_arm`
- Replications: `N=5` per model (20 production runs total)
- Output summary source of truth: `summary.json`
- Probe snapshots (one-shot checks):
  - `probe_current/`
  - `probe_legacy_earlier_run/`

Per production run, artifacts are flattened at top level as a 3-file set:

- `<agent>_runNN.json` -> run metadata (cost/runtime/classification)
- `<agent>_runNN.md` -> narrative/report text
- `<agent>_runNN.raw.json` -> raw provider payload

## When It Ran

Two production waves were executed:

- Wave 1 (overnight): 3-agent batch (`mistral`, `qwen`, `anthropic`) from `2026-05-22T23:41:32` to `2026-05-23T00:31:24`.
- Wave 2 (morning): OpenAI backfill (`openai`) from `2026-05-23T06:45:53` to `2026-05-23T07:00:34` after key availability was fixed.

Overall production window from file timestamps:

- Start: `2026-05-22T23:41:32`
- End: `2026-05-23T07:00:34`

## Who Uses This

Humans:

- Quick QA on cost, runtime, and output shape
- Cross-agent comparison before downstream evaluation

Bots:

- Machine-readable per-run metadata from `summary.json`
- Deterministic path structure for run artifacts (`*_runNN.json`, `*_runNN.md`, `*_runNN.raw.json`)

## Metric Definitions

- `has report`: `classification == "report"` from run metadata
- `parse OK`: markdown table parse heuristic succeeded (`#plants > 0`)
- `#plants`: heuristic count of markdown table data rows (`table_rows - 1 header`)
- `#sources`: heuristic count of unique `http(s)://` URLs in run markdown

These are operational heuristics for triage, not final scientific labels.

## Run Table

| model | rep# | cost_usd | duration_s | has report | parse OK | #plants | #sources |
|---|---:|---:|---:|:---:|:---:|---:|---:|
| claude-opus-4-6 | 1 | 0.8982 | 312.95 | yes | yes | 18 | 0 |
| claude-opus-4-6 | 2 | 0.9253 | 262.27 | yes | yes | 58 | 0 |
| claude-opus-4-6 | 3 | 0.9432 | 277.34 | no | yes | 81 | 0 |
| claude-opus-4-6 | 4 | 0.9305 | 282.83 | yes | yes | 5 | 0 |
| claude-opus-4-6 | 5 | 0.9130 | 295.01 | no | yes | 19 | 0 |
| mistral-large-2512 | 1 | 0.0380 | 195.29 | yes | yes | 54 | 15 |
| mistral-large-2512 | 2 | 0.2258 | 10.86 | no | no | 0 | 0 |
| mistral-large-2512 | 3 | 0.0012 | 11.26 | no | no | 0 | 0 |
| mistral-large-2512 | 4 | 0.1870 | 191.95 | yes | yes | 60 | 14 |
| mistral-large-2512 | 5 | 0.2831 | 133.74 | yes | yes | 33 | 9 |
| gpt-5.5 | 1 | 0.2673 | 174.00 | yes | yes | 114 | 7 |
| gpt-5.5 | 2 | 0.2658 | 181.33 | yes | yes | 103 | 20 |
| gpt-5.5 | 3 | 0.2437 | 172.99 | yes | yes | 133 | 15 |
| gpt-5.5 | 4 | 0.2604 | 189.51 | yes | yes | 128 | 14 |
| gpt-5.5 | 5 | 0.2219 | 149.27 | yes | yes | 121 | 10 |
| qwen3-max-2026-01-23 | 1 | 0.0429 | 212.84 | yes | yes | 70 | 11 |
| qwen3-max-2026-01-23 | 2 | 0.0476 | 236.60 | yes | yes | 71 | 10 |
| qwen3-max-2026-01-23 | 3 | 0.0444 | 220.52 | yes | yes | 65 | 15 |
| qwen3-max-2026-01-23 | 4 | 0.0498 | 247.02 | yes | yes | 75 | 14 |
| qwen3-max-2026-01-23 | 5 | 0.0507 | 251.86 | yes | yes | 74 | 10 |

## Summary Analysis

Headline:

- Total production runs: `20`
- Total cost: `$6.8398`
- Runs classified `report`: `16/20`

By model family:

- `gpt-5.5`: most consistent for this arm (`5/5` report, `5/5` parse OK), highest plant-yield heuristic (mean `119.8`).
- `qwen3-max-2026-01-23`: also consistent (`5/5` report, `5/5` parse OK), lower plant-yield than GPT-5.5 (mean `71.0`), with the longest mean runtime (`233.77s`).
- `mistral-large-2512`: mixed stability (`3/5` report, `3/5` parse OK), including two very short no-report outcomes.
- `claude-opus-4-6`: highest cost and long runtime; classifier says `3/5` report, but parse heuristic succeeds on all 5 runs, suggesting classifier/report-format mismatch on some outputs.

Caveats:

- `parse OK`, `#plants`, and `#sources` are heuristic extraction metrics from markdown, not adjudicated quality metrics.
- Final scientific claims should use the project evaluation pipeline, not this README-only triage layer.

## Research Notes

- Run segmentation: this dataset is a two-wave execution (overnight 3-agent batch, then morning OpenAI backfill after key availability fix). Treat wave boundaries as a possible confound in cross-model interpretation.
- Environment and credentials: OpenAI required loading `~/.config/keys/openai.env` and mapping `OPENAI_API_KEY_AEDIST` to `OPENAI_API_KEY` for the script invocation.
- Artifact consolidation: production artifacts were consolidated under this single directory; probe artifacts were retained for provenance in `probe_current/` and `probe_legacy_earlier_run/`.
- Classification mismatch risk: some runs classified as `no_report` still contain structured markdown content; classifier output and structure heuristics can disagree.
- Cost accounting: run-level `cost_usd` and `classifier_cost_usd` are both recorded; headline totals in this README report generation cost only unless explicitly stated otherwise.
- Runtime interpretation: `duration_s` in the table is wall-clock run time from metadata (`wall_s`), including API latency and harness overhead.
- Reproducibility anchor: use `summary.json` in this folder as the canonical machine-readable record for this run set.

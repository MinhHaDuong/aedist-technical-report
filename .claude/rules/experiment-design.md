# Experiment design rules — AEDIST

## Design for genericity

Lead with the generic abstraction; isolate the first application as a parameterized instance. Pipeline specs, architecture docs, and MASTERPLAN phases describe the general mechanism (Country X, Energy Subsector Y) first, then add "First application: ..." with country-specific details. Code: parameterize by country/subsector, don't hardcode PDP8/EVN details.

## Pinned reps are the control

When N reps are already pinned to the same value of a parameter (e.g. temperature=0.0), those reps **are** the reproducibility measurement for that parameter. Do not add a separate control or warmup call at the same value — it adds no information the existing reps are not already providing.

**Why:** Ticket 0073 proposed a warmup T=0 call before N T=0 reps. The user corrected in one sentence: the N reps' variance is the chain-reproducibility measurement.

## no_think is a sweep property, not a model property

`no_think` suppresses chain-of-thought for thinking-capable models. It belongs in `JobSpec` (per-sweep config in `experiments.toml`), not in the model registry (per-model metadata).

**Why:** Reasoning is a capability; whether to use it is an experimental choice. The same model may need thinking on for hard inference and thinking off for structured extraction.

**How to apply:** Do not add a `no_think` flag to model registry entries. Set `no_think = true` in sweep configs in `experiments.toml`. The harness injects `extra_body: {"think": false}` via `build_api_kwargs`.

## metrics dict is the complete scientific record (ADR-7)

`records_to_metrics()` in `measurements.py` is the single source of truth: all experimental conditions plus all result metrics. Figures and tables are projections that pick the columns they need.

**Why:** `measurements.jsonl` is only trustworthy as a source of truth if the metrics dict contains everything needed to diagnose confounds without re-reading raw JSON.

**How to apply:** When adding new run parameters, wire them into `records_to_metrics()` in the same merge request that adds them to `RunRecord`. Never define the metrics dict by what the paper currently shows. Bookkeeping-only fields excluded: `run_id`, `timestamp`, `result_file`, `validation`.

## MoE models require repeat=3

MoE models (DeepSeek V3.2, deepseek-v3, any 671B MoE) are non-deterministic even with `seed=42` and provider pinning. Completion token counts vary wildly across identical calls (e.g. 2308/3237/5443). Root cause: MoE tensor parallelism. `repeat=3` is mandatory for all cloud MoE sweeps. Do not reduce to `repeat=1` based on seed+provider pinning alone.

**Why:** Confirmed during merge request #278 (2026-04-22): 3 identical calls same prompt/model/seed/provider all produced different output lengths. Seed+provider pinning controls OpenRouter routing but not MoE kernel non-determinism.

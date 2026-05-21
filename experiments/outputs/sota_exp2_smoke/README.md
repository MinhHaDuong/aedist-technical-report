# SOTA Exp 2 smoke artefacts

Phase A (design) + Phase B (run) pairs from the Exp 2 SOTA smoke
(ticket 0185), one agent at a time. Distinct from the sibling
`../sota_smoke/` directory (which holds the per-adapter rollout smokes
from tickets 0167/0168/0169/0173 — single-call probes, no
Phase A / Phase B pairing).

## Filename convention

```
{agent}_meta_prompt.txt        # bytes sent to Phase A
{agent}_phase_a.raw.json       # raw provider response, Phase A
{agent}_phase_a.json           # parsed RunRecord, Phase A
{agent}_phase_a_design.json    # extracted {designed_prompt, settings, rationale}
{agent}_phase_b.raw.json       # raw provider response, Phase B
{agent}_phase_b.json           # parsed RunRecord, Phase B
```

`{agent}` ∈ `{mistral, qwen, openai, anthropic}`.

## How to regenerate

```bash
uv run python -m experiments.sota.exp2_interactive_smoke \
    --agent mistral --no-confirm
```

Drop `--no-confirm` for interactive (SPACE-gated) review.

## Scope

Single-pass smoke per agent, intended to validate end-to-end shape +
cost envelope before committing to a batch N=3 sweep (ticket 0199).
Not measurement data — these artefacts inform design decisions, they
do not feed `measurements.jsonl`.

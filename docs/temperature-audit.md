# Temperature Audit

Ticket 0084 — audit of LLM temperature settings across all experiments.

## Summary

Temperature is **recorded** in output JSON only for sweeps that use
`query_frontier.py` (which calls `build_api_kwargs`). All other query
scripts (`query.py`, `query_multiturn.py`, `query_rag.py`,
`query_web.py`, `query_decomposed.py`) pass **no temperature argument**
to the OpenAI API, relying on the provider default. The
`measurements.jsonl` file has 0 of 226 RunRecords with
`method_params.temperature` populated.

## Per-sweep audit

| Sweep | Query script | Temp in output JSON | Temp sent to API | Effective temperature | Output files |
|---|---|---|---|---|---|
| census | `query.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 111 |
| multiturn | `query_multiturn.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 24 |
| web | `query_web.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 15 |
| rag | `query_rag.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 27 |
| decomposed | `query_decomposed.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 14 |
| decomposed_v2 | `query_decomposed.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 17 |
| sourced | `query_rag.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 3 |
| frontier | `query_frontier.py` | **Yes (0.0)** | 0.0 via `build_api_kwargs` | 0.0 (reasoning models: omitted) | 12 |
| qualitative/scenarios | `query_frontier.py` | **Yes (0.0)** | 0.0 via `build_api_kwargs` | 0.0 (reasoning models: omitted) | 3 |
| qualitative/skill_plans | `query_frontier.py` | **Yes (0.0)** | 0.0 via `build_api_kwargs` | 0.0 (reasoning models: omitted) | 3 |
| ablation/parametric/* | `query_frontier.py` | **Yes (0.0)** | 0.0 via `build_api_kwargs` | 0.0 (reasoning models: omitted) | 26 |
| ablation/websearch/* | `query_frontier.py` | **Yes (0.0)** | 0.0 via `build_api_kwargs` | 0.0 (reasoning models: omitted) | 12 |
| ablation/rag/* | `query_rag.py` | No | Not sent (provider default) | Unspecified (typically 1.0) | 10 |
| verification | `query_verification.py` | No | N/A (post-processing) | N/A | 4 |

## Temperature handling by query script

| Script | `--temperature` flag | Default | Records in output | Notes |
|---|---|---|---|---|
| `query.py` | No | None (provider default) | No | Census/single-turn; no `build_api_kwargs` |
| `query_multiturn.py` | No | None (provider default) | No | Calls `query_single_turn` with no kwargs |
| `query_rag.py` | No | None (provider default) | No | Calls `query_single_turn` with no kwargs |
| `query_web.py` | No | None (provider default) | No | Calls `query_single_turn` with no kwargs |
| `query_decomposed.py` | No | None (provider default) | No | Calls `query_single_turn` with no kwargs |
| `query_frontier.py` | **Yes** | **0.0** | **Yes** | Uses `build_api_kwargs`; omits temp for reasoning models |
| `query_verification.py` | No | N/A | No | Post-processing, no LLM query (except self/cross modes) |

## Reasoning model behavior

`build_api_kwargs` (in `harness.py`) omits the `temperature` parameter for
models with `reasoning: true` in the registry. These models are:

- `qwen/qwen3-max-thinking`
- `moonshotai/kimi-k2-thinking`
- `z-ai/glm-5.1`
- `baidu/ernie-4.5-21b-a3b-thinking`
- `mistralai/mistral-small-2603` (marked reasoning in registry)
- `deepseek/deepseek-r1-0528`
- `openai/o3`

For these models, the provider controls the temperature internally (often
fixed at a low value). The frontier outputs still record `"temperature": 0.0`
in JSON, but for reasoning models this value was not actually sent to the API.

## measurements.jsonl

- 226 total RunRecords
- 0 have `method_params.temperature` populated (all are `null`)
- The `temperature` field exists in the `MethodParams` schema but is never
  written by any of the assemble/record scripts

## Provider defaults (when temperature is not sent)

The OpenAI API default is `temperature=1.0`. OpenRouter passes through
whatever the downstream provider uses, which is typically 1.0 for most
models. DeepSeek's API maps temperature=1.0 internally to their
recommended 0.3 for structured tasks (per DeepSeek documentation).

## Implications

1. **211 of 280 output files** (census, multiturn, web, rag, decomposed,
   sourced) used **unspecified temperature**, meaning the provider default
   (typically 1.0) was applied.
2. **69 output files** (frontier, qualitative, ablation parametric/websearch)
   used **temperature=0.0** explicitly.
3. The ablation study is internally inconsistent: parametric and websearch
   arms used t=0.0 (via `query_frontier.py`), but the RAG arm used
   unspecified temperature (via `query_rag.py`).
4. Run-to-run variance in census/rag/multiturn/web/decomposed sweeps
   conflates sampling noise (from t=1.0) with genuine model behavior
   differences.
5. `measurements.jsonl` never records temperature, making post-hoc
   analysis impossible without re-auditing output files.

## Recommendations (step 2 of ticket 0084)

1. Add `--temperature` flag to all query scripts, defaulting to 0.0.
2. Record temperature in every output JSON file.
3. Populate `method_params.temperature` in `measurements.jsonl` during
   assembly.
4. Document the limitation: existing census/rag/multiturn/web/decomposed
   runs used provider-default temperature (~1.0), not controlled.
5. For the article, state that temperature was controlled only in frontier
   and ablation parametric/websearch sweeps (t=0.0); all other sweeps
   used provider defaults.

# SOTA-agent smoke + probe artifacts

This directory holds single-call smoke tests and pricing probes from
the four SOTA-agent adapters under umbrella ticket 0166:

- `anthropic_*.json` — adapter 0167 (Claude Opus 4.7, web_search + adaptive thinking)
- `openai_*.json`    — adapter 0168 (GPT-5.x via Responses API, web_search + reasoning)
- `mistral_*.json`   — adapter 0169 (Mistral Large 2512, Agents API + web_search connector)
- `qwen_*.json`      — adapter 0173 (Qwen3-Max via DashScope, web_search in thinking mode)

## Scope

Smoke calls and pricing probes only — **not batch experiment runs**.
Batch runs land in sibling directories such as `../direct_complete/`,
`../rag_cited/`, and the Phase B output dirs added by 0170/0171.

## Filename convention

`<agent>_<YYYYMMDDTHHMMZ>.json`

Example: `anthropic_20260520T2030Z.json`. UTC timestamps, minute precision.

Each JSON file is a `RunRecord` (see `src/aedist/schema.py`) with
`agent_mode` set to `"smoke"` or `"probe"`.

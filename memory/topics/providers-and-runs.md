# Providers and runs — API quirks, local models, run mechanics

Scope: behaviour of model providers and of run tooling observed in this
project's sweeps. Registry of record: `experiments/models.yaml` and
`experiments/experiments.toml`.

## OpenRouter

- `reasoning_effort` (2026-05-21 probes): **absent** = fast mode, zero
  reasoning tokens; **`"minimal"` turns reasoning on** (lowest level of the
  enum, not an off switch); on a non-thinking model it is a no-op. For a
  "no reasoning" sweep send no effort key. Claude's extended thinking is not
  exposed through OpenRouter's unified field: use the Anthropic-direct route
  to probe it. The harness once stripped
  `usage.completion_tokens_details`, so reasoning tokens before PR #379 were
  never recorded.
- `*:free` models (Qwen, DeepSeek) rate-limit within seconds of a success,
  with windows of about ten minutes: run them serially with long pauses,
  never in parallel drains next to paid models; prefer the paid variant when
  pooling with historical data.

## Local models

- Local routing was set to move from Ollama to an OpenAI-compatible
  llama-server (author, 2026-05-21): the Ollama path is frozen, no new
  features or Ollama-specific validation. As of 2026-11-09 `models.yaml`
  still routes local entries through Ollama; migration status not checked.
- One local GPU job at a time on the workstation: parallel Ollama runs
  thrash VRAM. Check GPU occupancy before dispatch; run multi-model local
  sweeps sequentially. Cloud API parallelism is fine.
- `nohup` starts without the user's `PATH`: export `~/.local/bin` (where
  `uv` lives) explicitly.

## Run mechanics

- `aedist.smoke --promote-as-production` writes smoke calls under the worker
  naming (`{slug}-run{N}.json`, no smoke marker) so they ingest as
  production reps; it overwrites without warning and numbers from 1. Then
  extract, evaluate and assemble.
- Some background sessions inject `PYTEST_ADDOPTS=--cache-dir=…`, which this
  repo's pytest rejects: run `env -u PYTEST_ADDOPTS make check`. The usage
  error is environmental, not a regression.

## Sources

- Native notes: `project_openrouter_reasoning_effort.md` 427a16d3,
  `feedback_qwen_free_tier_rate_limit.md` dccc0415,
  `project_local_routing_llama_server.md` e7ea7a17, `feedback_padme_ollama_serial.md` 6d481b59,
  `feedback_nohup_path.md` d860aa16, `feedback_smoke_promote_production.md` e8ae26f0,
  `feedback_pytest_addopts_env_breaks_uv_pytest.md` 34f4bad3; native `MEMORY.md`
  key insight on provider quirks.
- Left out: the host-specific cache path of the `PYTEST_ADDOPTS` note and
  the workstation's hardware and directory lines of the native index
  (audience, [SOURCES.md](../SOURCES.md)).

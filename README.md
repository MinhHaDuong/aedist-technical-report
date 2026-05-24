# AEDIST Technical Report

Technical feasibility report for the **AEDIST** project (AI-driven Energy Data Integration for Sustainable Transition).

## About

This report (in French) evaluates AI technologies for tracking energy transitions in countries lacking robust statistical offices. It uses Vietnam's thermal power plant inventory (164 plants) as a benchmark case study.

The benchmark tests 73 AI models across multiple configurations: single-shot, multi-turn, RAG, and web-augmented — measuring recall, precision, F1, cost, and latency.

## Author

Minh Ha-Duong, CIRED – CNRS

## Structure

```
├── src/aedist/              # Python benchmark package
├── tests/                   # 1574 tests
├── experiments/             # Experiment pipeline
│   ├── experiments.toml     # Routers, model sets, and sweep configs
│   ├── models.yaml          # 73-model registry (single source of truth)
│   └── Makefile             # Sweep orchestration
├── data/reference/          # Ground truth CSVs
├── report/                  # LaTeX technical report
├── slides/                  # Beamer slides
├── Makefile                 # Root dispatcher
└── pyproject.toml           # Python package config
```

## Model routes

Each entry in `experiments/models.yaml` declares a `route:` field telling
the runner how to reach the model. Available routes:

| Route             | Auth                                | Notes                                                                                  |
|-------------------|-------------------------------------|----------------------------------------------------------------------------------------|
| `openrouter`      | `OPENROUTER_API_KEY`                | Default; OpenAI-compatible API. Covers most cloud models. Also the dispatch path for local `llama_server` (point `base_url` at the local endpoint). |
| `ollama`          | none (local)                        | Native `/api/chat` to honour `num_ctx`; serial only (Padme has one GPU). **Deprecated** in favour of `llama_server` via `openrouter` (OpenAI-compatible, no special path needed). |
| `anthropic`       | `ANTHROPIC_API_KEY`                 | Direct Anthropic Messages API; web-search via official tool. Ticket 0167.             |
| `openai-responses`| `OPENAI_API_KEY`                    | Direct OpenAI Responses API; web-search + reasoning. Ticket 0168.                     |
| `mistral-agents`  | `MISTRAL_API_KEY`                   | Direct Mistral Agents API; web-search connector. Ticket 0169.                         |
| `qwen-dashscope`  | `DASHSCOPE_API_KEY`                 | Direct Alibaba DashScope; thinking + web_search. Ticket 0173.                         |
| `claude-code-cli` | user's existing Claude Code session | Subprocess wrapper around `claude --print --bare`; no API key in sweep env. Ticket 0160. |

The `claude-code-cli` route is convenient for capability checks that
should not consume an `ANTHROPIC_API_KEY` budget: bills against the
user's subscription, runs in `--bare` mode (no hooks, no tools, no
`CLAUDE.md` context). Limitations: no temperature/seed/`max_tokens`
control, single-turn only. Registry entries:
`claude-sonnet-4-6-cli`, `claude-opus-4-7-cli`. Example sweep:
`sweep_smoke_claude_cli` in `experiments/experiments.toml`.

## Building

Requires [Tectonic](https://tectonic-typesetting.github.io/) and [uv](https://docs.astral.sh/uv/).

```bash
make test              # Run Python tests
make report            # Build report/report.pdf
make slides            # Build slides/slides.pdf
make tables            # Generate LaTeX tables from experiment results

# Experiments (from experiments/ directory):
cd experiments
make -j8 census        # Census: all models × 3 runs (parallel)
make rebuild-measurements  # Extract → evaluate all outputs → measurements.jsonl
```

## License

© 2026 Minh Ha-Duong. All rights reserved, work in progress not for redistribution.

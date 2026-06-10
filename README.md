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
| `anthropic`       | `ANTHROPIC_API_KEY`                 | Direct Anthropic Messages API; web-search via official tool.                           |
| `openai-responses`| `OPENAI_API_KEY`                    | Direct OpenAI Responses API; web-search + reasoning.                                   |
| `mistral-agents`  | `MISTRAL_API_KEY`                   | Direct Mistral Agents API; web-search connector.                                       |
| `qwen-dashscope`  | `DASHSCOPE_API_KEY`                 | Direct Alibaba DashScope; thinking + web_search.                                       |
| `claude-code-cli` | user's existing Claude Code session | Subprocess wrapper around `claude --print --bare`; no API key in sweep env.            |

The `claude-code-cli` route is convenient for capability checks that
should not consume an `ANTHROPIC_API_KEY` budget: bills against the
user's subscription, runs in `--bare` mode (no hooks, no tools, no
`CLAUDE.md` context). Limitations: no temperature/seed/`max_tokens`
control, single-turn only. Registry entries:
`claude-sonnet-4-6-cli`, `claude-opus-4-7-cli`. Example sweep:
`sweep_smoke_claude_cli` in `experiments/experiments.toml`.

## Building

Requires [Tectonic](https://tectonic-typesetting.github.io/) and [uv](https://docs.astral.sh/uv/).

### Build pipeline

The build runs in **four phases**, each owning a makefile. The root `Makefile`
holds the developer loop (tests, lint, coverage) plus the writing-side verbs CI
uses, and exposes the whole data pipeline through **exactly two cross-phase
entries**:

```bash
make staleness   # Dry-run report: what WOULD rebuild across P2+P3 (+P4).
                 # Touches nothing — always safe to run.
make world       # Deliberate, full re-run of P2+P3+P4. Runs P2 scoring for
                 # REAL (rewrites committed scored data — mart staleness):
                 # REVIEW the result via `git diff` before committing. Refuses
                 # to start on a dirty working tree. This is the project's
                 # reproducibility oracle: `make world && git diff --exit-code`.
```

`make world`/`make staleness` cover **P2→P3→P4 only**. **P1 (acquire) is
excluded** — it makes paid API calls, and a full re-run must never trigger a
money-costing re-acquisition. Re-acquire raw replies only by explicitly
invoking the P1 makefile.

Per-phase dev work invokes each phase makefile directly:

| Phase | Makefile | Invocation (from repo root) |
|-------|----------|-----------------------------|
| **P1 Acquire** (money-gated API sweeps) | `experiments/acquire.mk` | `make -C experiments -f acquire.mk <verb>` (the `-C experiments` is mandatory — the env/`.env`/`experiments.toml`/`jobs/` contract resolves relative to `experiments/`) |
| **P2 Score** (extract → evaluate → assemble) | `experiments/derived/score.mk` | `make -f experiments/derived/score.mk <verb>` |
| **P3 Render** (plot/tabulate → handoff artifacts) | `experiments/render.mk` | `make -f experiments/render.mk <verb>` |
| **P4 Write** (tectonic → PDFs) | `report/Makefile`, `slides/Makefile` | `make report` / `make slides` |

Common per-phase verbs:

```bash
make test                                                  # dev loop: Python tests
make report                                                # P4: build report/report.pdf (clean-room, committed artifacts)
make slides                                                # P4: build slides/slides.pdf
make -C experiments -f acquire.mk census                   # P1: census sweep, all models ($$ — see header)
make -f experiments/derived/score.mk rebuild-measurements  # P2: re-evaluate all outputs → measurements.jsonl
make -f experiments/derived/score.mk all-outcomes          # P2: all outcomes (mart + cross-evals + SC)
make -f experiments/render.mk report-tables                # P3: regenerate the report-side LaTeX tables
make -f experiments/render.mk all                          # P3: regenerate every committed handoff artifact
```

The five deleted convenience aliases (`tables`, `figures`, `select`, `census`,
`measurements`) are replaced by the explicit per-phase invocations above — the
phase makefiles are the single documented dev path.

The `experiments/models_selected.yaml` model-selection list (consumed by the P1
sweep configs in `experiments.toml` and `query_per_fuel.py`) is regenerated on
demand from the P2 mart:

```bash
uv run python -m aedist.select_models \
    --registry experiments/models.yaml --output experiments/models_selected.yaml --n 1
```

It has no makefile rule: it is *produced from* a P2 outcome but *configures* P1
sweeps, so a rule would couple two phases the build split keeps separate
(see `docs/pipeline-phases.md`).

## License

© 2026 Minh Ha-Duong. Released under the
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
licence — see the [`LICENCE`](LICENCE) file for the full legal text. You are free
to share and adapt this material for any purpose, including commercially, provided
you give appropriate credit (see [`CITATION.cff`](CITATION.cff)).

The Global Energy Monitor comparator data under `data/reference/` is © Global
Energy Monitor, redistributed under CC BY 4.0; see
`data/reference/PROVENANCE.md` for attribution details.

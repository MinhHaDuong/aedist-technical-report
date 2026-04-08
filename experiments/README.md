# Experiments

Benchmark pipeline for evaluating LLMs on Vietnamese thermal power plant
data extraction. Configures sweeps, dispatches jobs, and collects results.

## Configuration

| File | Purpose |
|------|---------|
| `experiments.toml` | Sweep definitions, model sets, router endpoints, paths |
| `models.yaml` | Registry of 52 models (name, provider, pricing, architecture) |

`experiments.toml` defines 9 sweep types under `[sweeps.*]`, each
specifying a query mode, prompt, model set, repeat count, and budget cap.

## Makefile targets

### Sweep pipelines

Each sweep follows a 3-phase pattern: `generate` (fan out jobs) →
`run` (execute queries) → `summary` (aggregate metrics).

| Target | Mode | Description |
|--------|------|-------------|
| `census` | single | All models, structured prompt, 3 runs |
| `regimes` | rag/multiturn/web | Information regime comparison |
| `decomposed` | decomposed | Split query by fuel type, merge |
| `verification` | verification | 5 provenance-checking modes |
| `sourced` | rag | RAG with citation extraction |
| `frontier` | frontier | Deep-research prompts, reasoning models |

### Analysis

| Target | Description |
|--------|-------------|
| `rebuild-measurements` | Re-extract + evaluate all outputs → `measurements.jsonl` |
| `self-consistency` | Majority/union vote analysis across repeat runs |

### Tools

| Target | Description |
|--------|-------------|
| `pdf2md PDF=file.pdf` | Convert a PDF to markdown for the RAG corpus |
| `build-corpus ITEMS=...` | Build corpus from Zotero PDFs |
| `preflight` | Check API keys, services (Ollama, GROBID), and dependencies |

## Directory layout

```
experiments/
├── experiments.toml    # sweep configs
├── models.yaml         # model registry
├── Makefile            # orchestration
├── data/               # test data + symlink to RAG corpus
├── outputs/            # JSON results per sweep (see outputs/README.md)
└── prompts/            # prompt templates (see prompts/README.md)
```

## Environment

API keys are loaded from `../.env` or `~/.claude/.env`:
`OPENROUTER_API_KEY`, `ZOTERO_API_KEY`, `TAVILY_API_KEY`.
OpenRouter concurrency defaults to 8 workers (override with `OR_MAX=N`).
Local models run via Ollama on `localhost:11434`.

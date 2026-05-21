# aedist

Python package for the AEDIST benchmark: querying LLMs, extracting
structured data from responses, and evaluating against reference tables.

## Module overview

### Query interfaces (`query_*.py`)

Each module implements one experimental mode. All share the harness
utilities and save JSON results to `experiments/outputs/`.

| Module | Mode | Description |
|--------|------|-------------|
| `query.py` | single | Direct structured query via OpenAI-compatible API |
| `query_rag.py` | rag | RAG: corpus injected as system context |
| `query_multiturn.py` | multiturn | Initial prompt + follow-up questions |
| `query_livesearch.py` | web | Web-search augmented (Tavily API) |
| `query_per_fuel.py` | decomposed | Split by fuel type, merge results |
| `query_direct.py` | frontier | Deep-research prompt for reasoning models |
| `query_verification.py` | verification | 5 provenance-checking modes |

### Core pipeline

| Module | Purpose |
|--------|---------|
| `harness.py` | Shared query utilities: client setup, budget tracking, save/skip logic |
| `evaluate.py` | CLI entry point (`evaluate`, `assemble`) |
| `manager.py` | Fan out sweep config into per-model job files |
| `worker.py` | Job execution with lease semantics (PadmeWorker, OpenRouterWorker) |
| `observer.py` | Monitor job board, detect stale leases, requeue expired jobs |

### Extraction and evaluation

| Module | Purpose |
|--------|---------|
| `extract.py` | Extract CSV tables from LLM JSON responses |
| `schema.py` | Canonical data schema (Plant, RunRecord, MatchType) |
| `reconcile.py` | Pipeline: schema validation → LP matching → metrics |
| `metrics.py` | Scoring: coverage, precision, F1, error taxonomy |
| `measurements.py` | Load and filter `measurements.jsonl` |
| `verify.py` | Provenance verification (tool, self, cross, web modes) |
| `self_consistency.py` | Majority/union vote across repeat runs |

### PDF converters (`pdf2md_*.py`)

Eight converter backends for building the RAG corpus from government PDFs.
All implement the `Converter` protocol defined in `pdf2md_utils.py`.

| Module | Backend | Local/Cloud |
|--------|---------|-------------|
| `pdf2md_grobid.py` | GROBID | local |
| `pdf2md_marker.py` | Marker | local (GPU) |
| `pdf2md_mineru.py` | MinerU | local (GPU) |
| `pdf2md_mistral_ocr.py` | Mistral OCR | cloud |
| `pdf2md_ollama.py` | Ollama vision | local |
| `pdf2md_openrouter.py` | OpenRouter vision | cloud |
| `pdf2md_openrouter_doc.py` | OpenRouter file-parser | cloud |
| `pdf2md_utils.py` | Shared protocol + utilities | — |

### Reporting (`tabulate_*.py`, `plot_*.py`)

Generate LaTeX tables and plot CSVs from `measurements.jsonl`.

| Module | Output |
|--------|--------|
| `tabulate_census.py` | Census longtable (sorted by F1) |
| `tabulate_comparaison.py` | Census vs RAG side-by-side |
| `tabulate_relances.py` | Multi-turn F1 progression |
| `tabulate_self_consistency.py` | Single-run vs majority/union vote |
| `tabulate_macros.py` | `\newcommand` macros for inline numbers |
| `tabulate_utils.py` | Shared label parsing utilities |
| `plot_census.py` | Census bar-chart CSV |
| `plot_cost_quality.py` | Cost × quality CSV + scatter (TP vs cost, Experiment 1) |

### Data processing

| Module | Purpose |
|--------|---------|
| `build_corpus.py` | Build RAG corpus from Zotero PDFs |
| `compare_converters.py` | Benchmark PDF converters side-by-side |
| `convert.py` | Legacy results → LaTeX conversion |
| `select_models.py` | Select top models with diversity constraints |
| `analyze_multiturn_budget.py` | Detect context window overflow in multi-turn outputs |
| `util.py` | Shared utilities (strip_diacritics, parse_number) |

## Subpackages

### `cleaner/`

Config-driven DataFrame normalization for power plant data. Applies
name, province, fuel, and status substitutions from `config.json`
(Vietnamese locale-aware patterns).

### `matching/`

Plant-level matching between LLM output and reference data.

| Module | Algorithm |
|--------|-----------|
| `lp.py` | Mixed-integer linear programming (MILP): binary assignment on name similarity + capacity closeness |
| `phased.py` | Fuzzy + exact matching with reconciliation utilities |

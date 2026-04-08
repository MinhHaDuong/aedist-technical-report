# Experiment outputs — table experiments

Primary LLM outputs: each file is one model's response for one run.
Files are named `{model}[-runN].json` with extracted `.csv` and `.eval.json`.

## Directories

| Directory | Sweep | Description |
|-----------|-------|-------------|
| `census/` | census | All models, structured prompt, 3 runs each |
| `rag/` | rag | RAG-augmented (wholesale corpus injection) |
| `multiturn/` | multiturn | Multi-turn with follow-up questions |
| `web/` | web | Web-search augmented (Tavily) |
| `decomposed/` | decomposed | Split by fuel type, merged |
| `sourced/` | sourced | RAG with citation extraction |
| `frontier/` | frontier | Deep-research prompt, reasoning models |

Derived analyses live in `../derived/`, qualitative experiments in `../qualitative/`.

Results are evaluated by `make rebuild-measurements`, which extracts CSVs
from the JSON and scores them against `data/reference/vietnam_thermal_v1.csv`.

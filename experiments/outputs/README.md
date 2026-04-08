# Experiment outputs

JSON result files organized by sweep type. Each file contains one model's
response for one run. Files are named `{model}[-runN].json`.

## Directories

| Directory | Sweep | Description |
|-----------|-------|-------------|
| `census/` | census | All models, structured prompt, 3 runs each |
| `rag/` | rag | RAG-augmented (wholesale corpus injection) |
| `multiturn/` | multiturn | Multi-turn with follow-up questions |
| `web/` | web | Web-search augmented (Tavily) |
| `decomposed/` | decomposed | Split by fuel type, merged |
| `sourced/` | sourced | RAG with citation extraction |
| `verification/` | verification | 5 provenance-checking modes |
| `frontier/` | frontier | Deep-research prompt, reasoning models |
| `frontier_scenarios/` | frontier | Scenario-based prompt variant |
| `frontier_skill/` | frontier | Skill-assessment prompt variant |
| `llm_direct/` | — | Legacy: early direct queries |
| `llm_multiturn/` | — | Legacy: early multi-turn queries |
| `rag_consistency/` | — | Self-consistency analysis outputs |
| `rag_curated/` | — | Curated corpus variant |

Results are evaluated by `make rebuild-measurements`, which extracts CSVs
from the JSON and scores them against `data/reference/vietnam_thermal_v1.csv`.

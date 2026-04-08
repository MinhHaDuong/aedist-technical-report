# Source data

Canonical data for the AEDIST benchmark: ground-truth reference tables
and the RAG corpus used as context in retrieval-augmented sweeps.

## `reference/`

Ground truth for evaluating model outputs.

| File | Description |
|------|-------------|
| `vietnam_thermal_v1.csv` | Plant-level reference (columns: `name,province,fuel,capacity_mwe,status,units_included`) |
| `vietnam_thermal_units_v1.csv` | Unit-level reference |
| `gem_thermal.csv` | GEM database plant-level extract (columns: `Name,Province,Fuel,Capacity,Status,Aggregated Units`) |
| `gem_units.csv` | GEM database unit-level extract |
| `GEM_aggregate.py` | Aggregates GEM unit rows into plant-level rows |
| `HDM_aggregate.py` | Normalizes plant names and aggregates units into plants |

Referenced in `experiments/experiments.toml` as `paths.reference`.

## `rag_corpus/`

18 markdown files extracted from Vietnamese government PDFs using Marker.
Sources include Power Development Plans (PDP7, PDP7A, PDP8), EVN annual
reports, and government studies/decisions. Each file contains markdown
tables preserving the original document structure.

Referenced by `experiments/experiments.toml` (`sweeps.rag.corpus`) and
`experiments/Makefile` (`CORPUS_OUTPUT`). To rebuild the corpus, run
`make build-corpus` from `experiments/`.

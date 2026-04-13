# Source data

Canonical data for the AEDIST benchmark: ground-truth reference tables
and the RAG corpus used as context in retrieval-augmented sweeps.

## `reference/`

Ground truth for evaluating model outputs.

| File | Description |
|------|-------------|
| `vietnam_thermal_v1.csv` | Plant-level reference (columns: `name,province,fuel,capacity_mwe,status,units_included` + classification columns) |
| `vietnam_thermal_units_v1.csv` | Unit-level reference |
| `gem_thermal.csv` | GEM database plant-level extract (columns: `Name,Province,Fuel,Capacity,Status,Aggregated Units` + classification columns) |
| `gem_units.csv` | GEM database unit-level extract |
| `GEM_aggregate.py` | Aggregates GEM unit rows into plant-level rows |
| `HDM_aggregate.py` | Normalizes plant names and aggregates units into plants |
| `add_classifications.py` | Adds IRES, ISIC, and PyPSA classification columns to plant-level CSVs |

Referenced in `experiments/experiments.toml` as `paths.reference`.

### International classification columns

Both `gem_thermal.csv` and `vietnam_thermal_v1.csv` include four
classification columns added by `add_classifications.py`:

| Column | Standard | Description |
|--------|----------|-------------|
| `ires_code` | IRES (UN, 2011) | Commodity code from the International Recommendations for Energy Statistics |
| `ires_label` | IRES (UN, 2011) | Human-readable commodity label |
| `isic_code` | ISIC Rev. 4 | International Standard Industrial Classification activity code |
| `pypsa_carrier` | PyPSA-Earth | Technology carrier string for PyPSA power system models |

### Fuel-to-classification mapping

| Fuel (CSV) | IRES code | IRES label | ISIC | PyPSA carrier |
|------------|-----------|------------|------|---------------|
| Coal / coal | 0121 | Hard coal | D3510 | coal |
| gas | 0311 | Natural gas | D3510 | CCGT |
| gas/oil | 0311 | Natural gas | D3510 | CCGT |

Dual-fuel (gas/oil) plants are classified by primary fuel (natural gas)
per IRES guidelines for multi-fuel plants. All thermal plants map to ISIC
D3510 (Electric power generation, transmission and distribution).

## `rag_corpus/`

18 markdown files extracted from Vietnamese government PDFs using Marker.
Sources include Power Development Plans (PDP7, PDP7A, PDP8), EVN annual
reports, and government studies/decisions. Each file contains markdown
tables preserving the original document structure.

Referenced by `experiments/experiments.toml` (`sweeps.rag.corpus`) and
`experiments/Makefile` (`CORPUS_OUTPUT`). To rebuild the corpus, run
`make build-corpus` from `experiments/`.

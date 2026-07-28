# aedist-bench — Benchmark for AI-Assisted Production of Economic Statistics

## Repository Structure

```
aedist-bench/
├── README.md
├── pyproject.toml
├── src/
│   └── aedist_bench/
│       ├── __init__.py
│       ├── schema.py          # Pydantic canonical schema
│       ├── normalize.py       # Name/capacity/status normalization
│       ├── match.py           # Exact + fuzzy matching pipeline
│       ├── metrics.py         # Coverage, precision, justification, error taxonomy
│       ├── reconcile.py       # Reconciliation table generation
│       ├── runner.py          # Standardized interface to run & evaluate any system
│       └── report.py          # Summary statistics + reconciliation CSV/Parquet output
├── data/
│   ├── reference/
│   │   ├── vietnam_thermal_v1.csv       # Expert-compiled gold standard
│   │   └── README.md                    # Dataset documentation, versioning notes
│   ├── corpus/
│   │   ├── curated/                     # Markdown tables from PDP7/7A/8, EVN reports
│   │   ├── extended/                    # + additional EVN annual reports, GEM tables
│   │   └── README.md                    # Corpus manifest: source, date, token count
│   └── aliases/
│       ├── plant_aliases.csv            # Known name variants → canonical name
│       └── province_aliases.csv         # Province name normalization table
├── prompts/
│   ├── prompt_1_singleshot.txt
│   ├── prompt_2_structured.txt
│   └── prompt_relance.txt
├── outputs/                             # System outputs (one CSV per run)
│   ├── llm_direct/
│   ├── llm_multiturn/
│   ├── rag_curated/
│   └── rag_extended/
├── results/
│   ├── reconciliation/                  # Per-run reconciliation tables
│   └── summary/                         # Aggregate metrics tables
├── tests/
│   ├── test_schema.py
│   ├── test_normalize.py
│   ├── test_match.py
│   └── test_metrics.py
├── paper/
│   ├── paper_benchmark_merged.md        # Article source
│   └── figures/
└── tasks.py                             # Invoke tasks: run, evaluate, report
```

## Quick Start

```bash
# Install
uv sync

# Evaluate a system output against the reference
aedist-bench evaluate outputs/rag_curated/claude_sonnet_run1.csv

# Run all baselines and generate summary
aedist-bench run-all --output results/
```

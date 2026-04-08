# AEDIST Technical Report

Technical feasibility report for the **AEDIST** project (AI-driven Energy Data Integration for Sustainable Transition).

## About

This report (in French) evaluates AI technologies for tracking energy transitions in countries lacking robust statistical offices. It uses Vietnam's thermal power plant inventory (164 plants) as a benchmark case study.

The benchmark tests 32 AI models across multiple configurations: single-shot, multi-turn, RAG, web-augmented, and verified — measuring recall, precision, F1, cost, and latency.

## Author

Minh Ha-Duong, CIRED – CNRS

## Structure

```
├── src/aedist/              # Python benchmark package
├── tests/                   # 61 tests
├── experiments/             # Experiment pipeline
│   ├── experiments.toml     # Routers, model sets, and sweep configs
│   ├── models.yaml          # 52-model registry (single source of truth)
│   └── Makefile             # Sweep orchestration
├── data/reference/          # Ground truth CSVs
├── report/                  # LaTeX technical report
├── slides/                  # Beamer slides (Econom'IA 2026)
├── Makefile                 # Root dispatcher
└── pyproject.toml           # Python package config
```

## Building

Requires [Tectonic](https://tectonic-typesetting.github.io/) and [uv](https://docs.astral.sh/uv/).

```bash
make test              # Run all 61 Python tests
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

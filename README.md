# AEDIST Technical Report

Technical feasibility report for the **AEDIST** project (AI-driven Energy Data Integration for Sustainable Transition).

## About

This report (in French) evaluates AI technologies for tracking energy transitions in countries lacking robust statistical offices. It uses Vietnam's thermal power plant inventory as a benchmark case study.

The report explores:
- **LLM limitations** for statistical data production
- **RAG (Retrieval Augmented Generation)** approaches
- **Knowledge graphs** for data traceability
- **Multi-agent systems** for complex data integration
- A proposed **hybrid architecture** combining these technologies

## Author

Minh Ha-Duong
CIRED – CNRS

## Building

Requires [Tectonic](https://tectonic-typesetting.github.io/) (XeTeX-based LaTeX engine).

```bash
make          # Build report.pdf
make tables   # Generate tables from aedist codebase
make clean    # Remove intermediate files
make cleaner  # Remove all generated files including PDF
```

## Structure

```
├── report.tex              # Main LaTeX document
├── refs.bib                # Bibliography (BibTeX)
├── inputs/                 # Supporting documents and data
├── Pictures/               # Figures
├── AssistantsComparison/   # AI assistant benchmark data
├── Experiments/            # Experimental results
└── aedist -> ...           # Symlink to aedist source code
```

## License

© 2026 Minh Ha-Duong. All rights reserved, work in progress not for redistribution.

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Census: 33 models, F1 2-66%, $0.73
- [x] Per-table pipeline: one script, one output, Make orchestrates (#43)
- [x] Fold experiments/scripts/ into src/aedist (#66, PR #70)
- [x] RAG corpus builder: Zotero → GROBID → Ollama (PR #71)
- [ ] Build RAG corpus and run Sweep 2 (#10)
- [ ] Cost data in Pareto chart (#59)
- [ ] Tabulate relances and comparaison (#47, #48)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Makefile: guard OPENROUTER_API_KEY only for sweep targets (#75)
- Chunked RAG strategy (currently only wholesale)
- Reasoning effort sweep (#11) — needs reasoning models on Padme
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors

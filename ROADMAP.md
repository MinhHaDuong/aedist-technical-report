## North star

Demonstrate — with reproducible quantitative evidence — what AI can and cannot do for statistical production, using Vietnam thermal power plants as benchmark. Present findings at Econom'IA 2026.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Monorepo — single self-contained repo
- [x] Test harness: query, extract, evaluate, verify (116 tests)
- [x] Model registry: 24 OpenRouter + 8 Padme local
- [x] Report restructured: 7 chapters, 410 lines
- [x] Census: 32 models evaluated (F1 range 2-66%, $0.73)
- [x] Per-table pipeline: one script per table/figure, Makefile orchestrates (#43)
- [ ] Pipeline UX: progress, checkpointing, parallelism (#22)
- [ ] Select top models: `make select` (#20)
- [ ] Information regime comparison — top models × 7 conditions (#10)
- [ ] Beamer slides with generated data (#15)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Chunked RAG strategy (currently only wholesale)
- Reasoning effort sweep — needs reasoning models on Padme (#11)
- Extend benchmark to other countries / sectors

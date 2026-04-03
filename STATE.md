Last updated: 2026-04-03

## Status

Pipeline end-to-end via Makefile. Census done (33 models, F1 2–66%, $0.73). 130 tests pass. Pareto chart wired to real cost data (PR #79).. Sweep 2 multiturn complete ($2.81). RAG corpus pipeline merged (PR #71): fully local via GROBID + Ollama. Sweep 2 RAG and web pending corpus build.

## Blockers

- Makefile OPENROUTER_API_KEY guard blocks non-OpenRouter targets (#75)

## Next actions

1. Build RAG corpus: `make build-corpus QUERY="quy hoạch điện"` (#10)
2. Run Sweep 2 RAG + web after corpus ready (#10)
4. Tabulate relances and comparaison after Sweep 2 (#47, #48)
5. Reframe slides: methods not models

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Census: 33 models, F1 2-66%, $0.73
- [x] Per-table pipeline: one script, one output, Make orchestrates (#43)
- [x] Fold experiments/scripts/ into src/aedist (#66, PR #70)
- [x] RAG corpus builder: Zotero → GROBID → Ollama (PR #71)
- [ ] Build RAG corpus and run Sweep 2 (#10)
- [x] Cost data in Pareto chart (PR #79)
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

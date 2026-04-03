Last updated: 2026-04-03

## Status

Pipeline end-to-end via Makefile. Census done (33 models, F1 2–66%, $0.73). 130 tests pass. Pareto chart wired to real cost data (PR #79). Sweep 2 multiturn complete ($2.81). RAG corpus pipeline merged (PR #71). PDF converters unified: 3 backends (grobid, ollama, openrouter) with shared Protocol-ready interface (PRs #80, #86). Corpus build attempted — GROBID failed on 16/18 scanned Vietnamese PDFs; only 2 usable docs.

## Blockers

- Makefile OPENROUTER_API_KEY guard blocks non-OpenRouter targets (#75)
- Padme: Ollama upgrade to 0.20.0 done, Gemma 4 model pull in progress

## Next actions

1. Build RAG corpus with vision converter once Gemma 4 pulled (#10)
2. Add Protocol interface + registry dispatch (#82)
3. Add Marker containerized backend (#83)
4. Add MinerU 3.x containerized backend (#84)
5. Table conversion benchmark across all backends (#85)
6. Run Sweep 2 RAG + web after corpus ready (#10)
7. Tabulate relances and comparaison after Sweep 2 (#47, #48)
8. Reframe slides: methods not models

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Census: 33 models, F1 2-66%, $0.73
- [x] Per-table pipeline: one script, one output, Make orchestrates (#43)
- [x] Fold experiments/scripts/ into src/aedist (#66, PR #70)
- [x] RAG corpus builder: Zotero → GROBID → Ollama (PR #71)
- [x] Cost data in Pareto chart (PR #79)
- [x] Unified PDF converter interface (PRs #80, #86)
- [ ] Layout-aware converters: Marker + MinerU (#81)
- [ ] Build RAG corpus and run Sweep 2 (#10)
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

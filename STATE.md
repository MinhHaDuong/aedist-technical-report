Last updated: 2026-04-06

## Status

Pipeline end-to-end via Makefile. Census done (35 models, F1 2–66%, $0.82). 336 tests pass. Sweep 2 RAG + multiturn complete ($2.81). Sweep 2 web complete ($0.13, #95 closed). CSV extraction tolerant of unfenced output and "Project" headers (#152). Self-consistency analysis merged (#96). Decomposition experiment: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Report + slides updated with decomposition findings (#151 merged). Abstract and conclusion chapters current.

## Blockers

- Padme: Gemma 4 model pulls still in progress (gemma4:26b + gemma4:31b) (#77)

## Next actions

1. Re-extract sweep2-web with tolerant extractor (GPT-5.4 now works)
2. Build RAG corpus with vision converter once Gemma 4 pulled (#10)
3. Reframe slides: methods not models, 11 condition axes (#93)
4. Add layout-aware PDF converters: Marker + MinerU (#81, #83, #84)
5. Table conversion benchmark across backends (#85)

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Census: 33 models, best F1 66%
- [x] Gold truth RAG corpus: 18 tables from official sources
- [x] Sweep 2 RAG + multiturn: complete
- [x] Self-consistency analysis: majority/union vote pipeline (#96)
- [x] Worker infrastructure: PadmeWorker + OpenRouterWorker + Observer
- [x] Unified PDF converter interface with Protocol registry
- [x] Decomposition experiment: 99% F1 at $0.06 (#151)
- [x] Report + slides: decomposition findings, updated conclusion + abstract
- [ ] Layout-aware converters: Marker + MinerU (#81)
- [ ] Build RAG corpus and run Sweep 2 (#10)
- [ ] Reframe slides for methods-not-models (#93)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Reasoning effort sweep (#11) — needs reasoning models on Padme
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors
- Retire Makefile sweep dispatch in favor of Workers (ticket 0011)

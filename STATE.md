Last updated: 2026-04-06

## Status

Pipeline end-to-end via Makefile. Census: 35 models (25 cloud + 10 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 393 tests pass. Sweep 2 complete: RAG ($2.81), multiturn, web ($0.13). Decomposition experiment: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Marker converter tested on Decision 1509: 170 tables extracted. Web portal test: Vietnamese gov data is in PDF annexes, not HTML. Reporting refactored to measurements.jsonl (#157). All review findings fixed (#159).

## Blockers

- MinerU container image still pulling (Padme network)

## Next actions

1. Start MinerU container when pull completes, test on Decision 1509
2. Reframe slides: methods not models, 11 condition axes (#93)
3. Add Perspectives section to report (#116)
4. Stack decomposition + union vote + precision filter

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Census: 35 models, best F1 98.4%
- [x] Sweep 2: RAG + multiturn + web complete
- [x] Decomposition experiment: 99% F1 at $0.06
- [x] Self-consistency: union > majority (recall-bottlenecked)
- [x] Marker converter: 170 tables from Decision 1509
- [x] Converter benchmark: Marker >> GROBID for tables (#85)
- [x] Web portal test: gov data in PDFs, not HTML (#114)
- [x] Report + slides updated with all findings
- [ ] MinerU converter test (#81, #111 — container pulling)
- [ ] Reframe slides for methods-not-models (#93)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Reasoning effort sweep (#11)
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors
- Retire Makefile sweep dispatch in favor of Workers (ticket 0011)

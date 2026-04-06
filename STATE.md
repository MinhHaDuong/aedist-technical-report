Last updated: 2026-04-06

## Status

Pipeline end-to-end via Makefile. Census: 35 models (25 cloud + 10 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 423 tests pass. Sweep 2 complete: RAG ($2.81), multiturn, web ($0.13). Decomposition experiment: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Converter benchmark: 6 backends tested on Decision 1509 — Marker (170 tables) and Mistral OCR direct (169 tables) are the top two (#85, #167). MinerU tested: good text, 0 tables. Reporting refactored to measurements.jsonl (#157).

## Blockers

None

## Next actions

1. Reframe slides: methods not models, 11 condition axes (#93)
2. Add Perspectives section to report (#116)
3. Stack decomposition + union vote + precision filter
4. Update report with converter benchmark findings (6 backends)

## North star

Build a generic pipeline that produces primary-sourced, auditable statistical tables from open sources — for any country and energy subsector. First application: Vietnam thermal plants. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Census: 35 models, best F1 98.4%
- [x] Sweep 2: RAG + multiturn + web complete
- [x] Decomposition experiment: 99% F1 at $0.06
- [x] Self-consistency: union > majority (recall-bottlenecked)
- [x] Converter benchmark: Marker + Mistral OCR direct >> GROBID, MinerU, OpenRouter plugin (#85, #167)
- [x] Web portal test: gov data in PDFs, not HTML (#114)
- [x] Report + slides updated with all findings
- [ ] Reframe slides for methods-not-models (#93)

## Next milestone

Primary-source pipeline (#98): generic extraction from government documents, first application on Vietnam thermal.

## Backlog

- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Reasoning effort sweep (#11)
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors
- Retire Makefile sweep dispatch in favor of Workers (ticket 0011)
- Journal submission (after pipeline produces first auditable table)

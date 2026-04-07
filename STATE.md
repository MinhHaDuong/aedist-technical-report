Last updated: 2026-04-07

## Status

Pipeline end-to-end via Makefile. Census: 37 models (26 cloud + 11 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 459 tests pass. Sweep 2 complete: RAG ($2.81), multiturn, web ($0.13). Decomposition: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Converter benchmark: 6 backends on Decision 1509 — Marker (170 tables) and Mistral OCR direct (169) top two; MinerU GPU fixed, 62 tables but diacritics stripped in table cells (#178). Benchmark table added to report section 3.3. Frontier bench merged (#179): 14 models × 3 prompts, $2.34 total. RAG local sweep in progress. Slides reframed (#93, #171). All reporting reads from measurements.jsonl. Model registry sprawl: 8 YAML files (ticket 0022).

## Blockers

None

## Next actions

1. Visual review: `make slides` and check PDF renders correctly
2. Add Perspectives section to report (#116)
3. Reframe slides "Next steps" as benchmark→pipeline arc (#115)
4. Complete RAG local sweep: 2B/4B scaling curve (branch t21-rag-local-models)

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Converter benchmark table added to report (#85, #178)
- [ ] Visual PDF review of slides (no LaTeX on Padme)
- [ ] Reframe slides "Next steps" (#115)
- [ ] Perspectives section in report (#116)
- [ ] RAG local sweep: 2B/4B/9B scaling curve (branch t21-rag-local-models)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Consolidate model registry into single YAML with filters (ticket 0022)
- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors
- Retire Makefile sweep dispatch in favor of Workers (ticket 0011)

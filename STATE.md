Last updated: 2026-04-07

## Status

Pipeline end-to-end via Makefile. Census: 37 models (28 cloud + 9 local), best F1 98.2% (Claude Opus 4.6). 458 tests pass. Slides use generated macros from census CSV — model counts, plant ranges auto-update. Metropolis sub-themes eliminate 1164 font-scan warnings (#185). Sweep 2 complete: RAG, multiturn, web. Decomposition: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Converter benchmark: 6 backends on Decision 1509. Sweep 5 (sourced extraction) added. All reporting reads from measurements.jsonl. Zotero library deduplicated: 358 items trashed (tiers 1–3), Decision 1509 cataloguing aligned.

## Blockers

None

## Next actions

1. Add Perspectives section to report (#116)
2. Reframe slides "Next steps" as benchmark→pipeline arc (#115)
3. Complete RAG local sweep: 2B/4B scaling curve (branch t21-rag-local-models)
4. Drop unicode-math from report.tex (#186)

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Converter benchmark table added to report (#85, #178)
- [x] Slides macros pipeline + font warning fix (#185)
- [ ] Reframe slides "Next steps" (#115)
- [ ] Perspectives section in report (#116)
- [ ] RAG local sweep: 2B/4B/9B scaling curve (branch t21-rag-local-models)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors
- Retire Makefile sweep dispatch in favor of Workers (ticket 0011)
- Drop unicode-math from report.tex (#186)

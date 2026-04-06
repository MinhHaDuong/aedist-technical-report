Last updated: 2026-04-06

## Status

Pipeline end-to-end via Makefile. Census: 35 models (26 cloud + 9 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 450 tests pass. Sweep 2 complete: RAG ($2.81), multiturn, web ($0.13). Decomposition experiment: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Converter benchmark: 6 backends on Decision 1509 — Marker (170 tables) and Mistral OCR direct (169 tables) top two (#167). Slides reframed for methods-not-models (#93, #171). All reporting scripts read from measurements.jsonl (#157, #165, #174).

## Blockers

None

## Next actions

1. Visual review: `make slides` and check PDF renders correctly
2. Add Perspectives section to report (#116)
3. Reframe slides "Next steps" as benchmark→pipeline arc (#115)
4. Extend RAG to local models (#10, in progress)

## North star

Build a generic pipeline that produces primary-sourced, auditable statistical tables from open sources — for any country and energy subsector. First application: Vietnam thermal plants. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Slides reframed: 5 condition axes, self-consistency, methods > models (#93, #171)
- [x] Converter benchmark: 6 backends, Marker + Mistral OCR direct (#85, #167)
- [x] Data fixes: pareto costs, census filtering, multiturn populated (#171 review)
- [ ] Visual PDF review of slides (no LaTeX on Padme)
- [ ] Reframe slides "Next steps" (#115)
- [ ] Perspectives section in report (#116)

## Next milestone

Primary-source pipeline (#98): generic extraction from government documents, first application on Vietnam thermal.

## Backlog

- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors
- Retire Makefile sweep dispatch in favor of Workers (ticket 0011)
- Journal submission (after pipeline produces first auditable table)

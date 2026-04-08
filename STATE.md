Last updated: 2026-04-08

## Status

Pipeline end-to-end via manager+worker dispatch. Census: 37 models (26 cloud + 11 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 551 tests pass. RAG ($2.81), multiturn, web ($0.13) complete. Decomposition: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Converter benchmark: 6 backends on Decision 1509 — Marker (170 tables) and Mistral OCR direct (169) top two. Frontier bench merged (#179): 14 models × 3 prompts, $2.34 total. RAG local sweep in progress. All reporting reads from measurements.jsonl (246 entries) via `aedist.measurements` module. Config consolidated: single experiments.toml (model registry + conditions + paths). Experiments reorganized (#198): outputs/ (table experiments only), derived/ (rag_consistency, verification), qualitative/ (scenarios, skill_plans). Extract pipeline hardened: skip-check before parsing, locale-aware capacity normalization (util.parse_number), diacritics stripping (util.strip_diacritics), CRLF-safe regex, ExtractStatus enum. 102 extract/util tests. Evaluation refactored (#196): Make pattern rules (evaluate + assemble), parallelism via `make -j`. Report LaTeX cleaned: unicode-math dropped, replaced with explicit fontspec+amsmath (#197).

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

- [x] Glossary added to report (#190)
- [ ] Visual PDF review of slides (no LaTeX on Padme)
- [ ] Reframe slides "Next steps" (#115)
- [ ] Perspectives section in report (#116)
- [ ] RAG local sweep: 2B/4B/9B scaling curve (branch t21-rag-local-models)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Smart worker dispatch: self-select by capability (ticket 0023)
- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors

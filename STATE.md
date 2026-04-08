Last updated: 2026-04-08

## Status

Pipeline end-to-end via manager+worker dispatch. Census: 35 models (25 cloud + 10 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 574 tests pass. RAG ($2.81), multiturn, web ($0.13) complete. Decomposition: DeepSeek V3.2 163/163 plants, F1=98.8%, $0.06. Converter benchmark: 6 backends on Decision 1509 — Marker (170 tables) and Mistral OCR direct (169) top two. Frontier bench merged (#179): 14 models × 3 prompts, $2.34 total. RAG local sweep in progress. All reporting reads from measurements.jsonl via `aedist.measurements` module. Config consolidated: single experiments.toml (model registry + conditions + paths). Registry swept (#199): 6 broken/obsolete models removed (52→46), data purged. Experiments reorganized (#198): outputs/ (table experiments only), derived/ (rag_consistency, verification), qualitative/ (scenarios, skill_plans). Extract pipeline hardened: .eval.json filter, multiturn joins all assistant turns, pipe tables split per-table, project_name/plant_name_project mapped. 16 missing CSVs recovered (9 frontier, 3 multiturn, 4 web); 11 orphans classified: 8 refusal, 3 error (#203). Evaluation refactored (#196): Make pattern rules (evaluate + assemble), parallelism via `make -j`. Orphan JSON status split (#203): refusal/error/empty replace catch-all "qualitative". Report LaTeX cleaned: unicode-math dropped, replaced with explicit fontspec+amsmath (#197). Perspectives section and slides updated (#202).

## Blockers

None

## Next actions

1. Visual review: `make slides` and check PDF renders correctly
2. Complete RAG local sweep: 2B/4B scaling curve (branch t21-rag-local-models)
3. Handle empty CSVs gracefully (ticket 0045)

## North star

Benchmark *methods* — not just models — for producing statistical infrastructure tables from open sources. Present findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [ ] Visual PDF review of slides (no LaTeX on Padme)
- [ ] RAG local sweep: 2B/4B/9B scaling curve (branch t21-rag-local-models)

## Next milestone

Submit to journal (TBD — after conference feedback).

## Backlog

- Reflexive self-prompting experiment (ticket 0038)
- Audit JSON globs for .eval.json filtering (ticket 0044)
- Handle empty CSVs gracefully in evaluate (ticket 0045)
- Smart worker dispatch: self-select by capability (ticket 0023)
- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Verification sweep (#12)
- Sensitivity analysis (#13)
- Extend benchmark to other countries / sectors

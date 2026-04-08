Last updated: 2026-04-08

## Status

Pipeline end-to-end via manager+worker dispatch. Census: 35 models (25 cloud + 10 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 574 tests pass. Frontier bench: 14 models × 3 prompts, $2.34 total. Slides reframed as pilot study: obvious-approach motivation, 4-level evaluation framework, limitations-as-specs, verification-vs-pipeline argument, epistemic accountability. Report Perspectives expanded to ~1 page: pilot accuracy, trust gate, power system scope, ASEAN scaling, pipeline rationale. Tickets 0026/0027 closed, 0034/0035 created (statistical hygiene). Orphan JSON status split (#203): refusal/error/empty replace catch-all "qualitative".

## Blockers

None

## Next actions

1. Visual review: `make slides` and check PDF renders correctly
2. Fix remaining 99% → 98.8% inconsistencies in slides (ticket 0036)
3. Complete RAG local sweep: 2B/4B scaling curve (branch t21-rag-local-models)
4. Bootstrap CIs and paired significance tests (ticket 0034)
5. Matching sensitivity sweep (ticket 0035, blocked by 0034)

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. Not which model is best, but which **method** produces a trustworthy statistical table. Present pilot findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Reframe slides as pilot study (#115, #193)
- [x] Perspectives section in report (#116)
- [ ] Visual PDF review of slides
- [ ] RAG local sweep: 2B/4B/9B scaling curve (branch t21-rag-local-models)

## Next milestone

Statistical hygiene (tickets 0034, 0035) → journal submission (TBD — after conference feedback).

## Backlog

- Standardize 99% → 98.8% in slides (ticket 0036)
- Bootstrap CIs and significance tests (ticket 0034)
- Matching sensitivity sweep (ticket 0035)
- Rewrite MASTERPLAN phases (phases 2, 4 done; need statistical validation phase)
- Handle empty CSVs gracefully in evaluate (ticket 0045)
- Reflexive self-prompting experiment (ticket 0038)
- Audit JSON globs for .eval.json filtering (ticket 0044)
- Smart worker dispatch: self-select by capability (ticket 0023)
- Stack decomposition + union vote + precision filter
- Chunked RAG strategy (currently only wholesale)
- Verification sweep (#12)
- Extend benchmark to other countries / sectors

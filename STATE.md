Last updated: 2026-04-10

## Status

Pipeline end-to-end via manager+worker dispatch. Census: 37 models (26 cloud + 11 local), best F1 98.4% (Qwen 3.5 9B local), $0.82 total. 861 tests pass. Method convergence strip plot added (PR #219): 1 dot = 1 plant, matplotlib PDF. Data dedup fix: `_extracted` prompt_version was duplicating RAG data in measurements. matplotlib added as main dependency.

## Blockers

None

## Next actions

1. Visual review: `make slides` — check all pages render correctly
2. Complete RAG local sweep: 2B/4B scaling curve (branch t21-rag-local-models)
3. Matching sensitivity sweep (ticket 0035)
4. Fix empty CSV crash in evaluate (ticket 0045)
5. Investigate RAG/_extracted measurement duplication (ticket 0048)

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. Not which model is best, but which **method** produces a trustworthy statistical table. Present pilot findings at Econom'IA 2026. See MASTERPLAN.md for the long-term vision.

## Current milestone: Econom'IA 2026 (April 11)

- [x] Reframe slides as pilot study (#115, #193)
- [x] Perspectives section in report (#116)
- [x] Fix 99% → 98.8% consistency (ticket 0046)
- [x] Method convergence strip plot (ticket 0031, PR #219)
- [ ] Visual PDF review of slides
- [ ] RAG local sweep: 2B/4B/9B scaling curve (branch t21-rag-local-models)

## Next milestone

Statistical hygiene (ticket 0035) → journal submission (TBD — after conference feedback).

## Open tickets (9)

- 0021 Test local models with RAG wholesale on Padme
- 0023 Smart worker dispatch (infra)
- 0025 Sourced extraction with citation scoring
- 0029 Sensitivity analysis sweep
- 0030 Verification regimes sweep
- 0035 Matching sensitivity sweep (doing)
- 0038 Reflexive self-prompting experiment
- 0045 Empty CSV crash in evaluate
- 0048 RAG/_extracted measurement duplication (new)

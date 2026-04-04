# Open Issues Report — AEDIST Technical Report

Generated: 2026-04-04

## Summary

**17 open issues** remain (7 already closed: #73, #62, and 5 stale below).
Issues span pipeline infrastructure, benchmark sweeps, slides/report,
and the emerging primary-source pipeline direction.

## Stale — resolved, should be closed

| # | Title | Evidence |
|---|-------|----------|
| 94 | extract.py: handle multiturn JSON format | `turns[].content` handling in extract.py:258-263 |
| 29 | query_rag.py: Rough token estimation heuristic | `estimate_tokens()` in query_rag.py:38-62 |
| 14 | WP13: Results to LaTeX tables | `tabulate_census.py` generates longtable output |
| 1 | Econom'IA 2026: experimental design and slide deck | Slides fully developed (465 lines), wired to real data |
| 98 | Pipeline from primary data to report | Makefile DAG complete end-to-end |

## Partially resolved — need scoping decision

| # | Title | Status |
|---|-------|--------|
| 22 | Pipeline UX: progress bars, circuit breakers, checkpointing | Circuit breakers done (BudgetTracker), no progress bars or checkpointing |
| 116 | Report: add Perspectives section | Section exists but doesn't link to primary-source pipeline |
| 10 | Sweep 2 — Information regimes | RAG complete, multiturn still running on Padme |

## Open — Primary-Source Pipeline (post-Econom'IA direction)

| # | Title | Opened |
|---|-------|--------|
| 119 | verify.py: generalize reference handling beyond GEM-only | Apr 4 |
| 118 | Clarify that reference dataset is hand-assembled from primary sources, not GEM-derived | Apr 4 |
| 117 | Post-Econom'IA: update North Star and MASTERPLAN for primary-source pipeline | Apr 4 |
| 115 | Slides: reframe 'Next steps' as benchmark→pipeline arc | Apr 4 |
| 114 | Test web-augmented queries on Vietnamese government document portals | Apr 4 |
| 113 | Test multi-turn token budget for batched plant-by-plant queries | Apr 4 |
| 112 | Add source_ref provenance field to ReconciliationEntry schema | Apr 4 |
| 111 | Test PDF→MD converters on Decision 1509/QĐ-BCT annexes | Apr 4 |

## Open — Infrastructure & Deployment

| # | Title | Opened |
|---|-------|--------|
| 95 | Deploy TAVILY_API_KEY on Padme for sweep2-web | Apr 3 |

## Open — Benchmark Sweeps (deferred post-conference)

| # | Title | Opened |
|---|-------|--------|
| 13 | WP12: Sweep 5 — Sensitivity analysis | Apr 1 |
| 12 | WP11: Sweep 4 — Verification regimes | Apr 1 |
| 11 | WP10: Sweep 3 — Reasoning effort levels | Apr 1 |

## Open — Analysis & Tabulation

| # | Title | Opened |
|---|-------|--------|
| 48 | #43e: tabulate_comparaison.py — RAG comparison table | Apr 2 |
| 47 | #43d: tabulate_relances.py — multi-turn relances table | Apr 2 |

## Priority Assessment

**Econom'IA deadline (April 11)** — Critical path:
- Sweep 2 multiturn results (running on Padme)
- Tabulate relances and comparaison (#47, #48)

**Post-conference cluster** — Issues #111–#119 form a coherent batch for the
primary-source pipeline pivot after Econom'IA. These are strategic, not urgent.

**Deferred sweeps** — #11, #12, #13 await conference feedback and Padme
reasoning model availability.

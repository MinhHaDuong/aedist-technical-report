# Open Issues Report — AEDIST Technical Report

Generated: 2026-04-04

## Summary

**24 open issues** across the repository, spanning pipeline infrastructure,
benchmark sweeps, slides/report, and the emerging primary-source pipeline direction.

## Issues by Theme

### Primary-Source Pipeline (post-Econom'IA direction)

| # | Title | Opened |
|---|-------|--------|
| 119 | verify.py: generalize reference handling beyond GEM-only | Apr 4 |
| 118 | Clarify that reference dataset is hand-assembled from primary sources, not GEM-derived | Apr 4 |
| 117 | Post-Econom'IA: update North Star and MASTERPLAN for primary-source pipeline | Apr 4 |
| 116 | Report: add Perspectives section linking benchmark to primary-source pipeline | Apr 4 |
| 115 | Slides: reframe 'Next steps' as benchmark→pipeline arc | Apr 4 |
| 114 | Test web-augmented queries on Vietnamese government document portals | Apr 4 |
| 113 | Test multi-turn token budget for batched plant-by-plant queries | Apr 4 |
| 112 | Add source_ref provenance field to ReconciliationEntry schema | Apr 4 |
| 111 | Test PDF→MD converters on Decision 1509/QĐ-BCT annexes | Apr 4 |

### Pipeline & Infrastructure

| # | Title | Opened |
|---|-------|--------|
| 98 | Pipeline from primary data to report | Apr 3 |
| 95 | Deploy TAVILY_API_KEY on Padme for sweep2-web | Apr 3 |
| 94 | extract.py: handle multiturn JSON format (turns[].content) | Apr 3 |
| 22 | Pipeline UX: progress bars, circuit breakers, checkpointing | Apr 2 |

### Benchmark Sweeps

| # | Title | Opened |
|---|-------|--------|
| 13 | WP12: Sweep 5 — Sensitivity analysis | Apr 1 |
| 12 | WP11: Sweep 4 — Verification regimes | Apr 1 |
| 11 | WP10: Sweep 3 — Reasoning effort levels | Apr 1 |
| 10 | WP9: Sweep 2 — Information regimes (top 5 models × 7 conditions) | Apr 1 |

### Analysis & Tabulation

| # | Title | Opened |
|---|-------|--------|
| 48 | #43e: tabulate_comparaison.py — RAG comparison table | Apr 2 |
| 47 | #43d: tabulate_relances.py — multi-turn relances table | Apr 2 |
| 29 | query_rag.py: Rough token estimation heuristic | Apr 2 |
| 14 | WP13: Results to LaTeX tables | Apr 1 |

### Slides & Report

| # | Title | Opened |
|---|-------|--------|
| 62 | Slides: fix 1000+ XeTeX font scan warnings | Apr 2 |

### Code Quality

| # | Title | Labels | Opened |
|---|-------|--------|--------|
| 73 | plot_census.py: remove unused slug_from_label import | enhancement | Apr 3 |

### Meta / Milestones

| # | Title | Opened |
|---|-------|--------|
| 1 | Econom'IA 2026: experimental design and slide deck | Apr 1 |

## Priority Assessment

**Econom'IA deadline (April 11)** — Per STATE.md, the critical path items are:
- Sweep 2 multiturn results (running on Padme)
- Tabulate relances and comparaison (#47, #48)

**Blockers noted in STATE.md** (not tracked as issues):
- Makefile OPENROUTER_API_KEY guard blocks non-OpenRouter targets (#75 — closed)
- evaluate-all overwrites all_metrics.json instead of appending (#92 — closed)
- Padme: Gemma 4 model pulls still in progress

**Post-conference cluster** — Issues #111–#119 form a coherent batch for the
primary-source pipeline pivot after Econom'IA. These are strategic, not urgent.

Last updated: 2026-04-13 (hygiene session)

## Status

Pipeline end-to-end. Census: 37 models, best F1 98.8%. Three-regime ablation Phase 1 complete. Base-vs-census analysis shipped (PR #238, n=9, ΔF1=+17.3pp [+8.4,+25.1]). PR #239 merged: coherence checks, FDR correction, ANOVA diagnostics, 12 new tickets (0075-0086), quality-grounding doc. Repo hygiene: 15 worktrees removed, 85+ branches pruned, orphaned data rescued (qwen3.5:2b/4b RAG runs). Ticket 0021 reframed as pipeline de-risking (two families × three tiers), cloud runs in progress.

## Blockers

None

## Next actions

1. Ticket 0021: RAG scaling curve — cloud runs in progress (worktree), Padme edge runs next
2. Ticket 0068: decomposition hallucination fix — evaluate 17 existing probe outputs, write dynamic table
3. Phase 2 decision: run RAG-only ablation (16 prompts, Kimi K2 + DeepSeek V3.2, ~$5-10)
4. Visual review: `make slides` + `make report` — check for build errors

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. Not which model is best, but which **method** produces a trustworthy statistical table. See MASTERPLAN.md for the long-term vision.

## Current milestone: Journal submission (post-conference)

- [x] Variance decomposition: method dominates model, eta_sq=0.50 vs 0.07 (PR #228)
- [x] Matching sensitivity: 35 rank flips, 17-model stable core (PR #231)
- [x] Ablation hypotheses preregistered (PR #230)
- [x] Capability flags + web search in harness (PR #234)
- [x] prompt_modules wired in query_frontier + query_rag (PRs #229, #235)
- [x] Three-regime ablation model sets: dev + journal tiers (PR #236)
- [x] Phase 1 selection: 3 regimes x 3 models, HUMAN GATE delivered (PR #237)
- [x] Regime linkage documented in report (PR #233)
- [x] Multi-agent verification protocol designed (PR #232)
- [x] Base vs census gap analysis (ticket 0057, PR #238)
- [x] Coherence checks + statistical rigor fixes (PR #239)
- [ ] RAG scaling curve: two families, edge-to-cloud (ticket 0021, in progress)
- [ ] Decomposition hallucination fix evaluation (ticket 0068)
- [ ] Phase 2 ablation: 16 prompts on RAG regime (awaiting human decision)
- [ ] Multi-agent verification Phase B (ticket 0059)
- [ ] Full verification factorial (ticket 0060)
- [ ] Ablation results visualization (ticket 0067)

## Open tickets (19)

- 0021 RAG scaling: two families × three tiers (doing — cloud runs in worktree, Padme queued)
- 0059 Multi-agent verification Phase B (ready)
- 0060 Full verification factorial (ready)
- 0067 Ablation results visualization (blocked by Phase 2)
- 0068 Decomposition hallucination fix (doing — 17 probe outputs need evaluation)
- 0069 Project namespace audit (ready)
- 0073 Optional warmup run (blocked by 0072, now closed)
- 0075 Universal prompt optimization survey (ready)
- 0076 LangChain Deep Agents evaluation (ready)
- 0077 Lit review: automated statistics for PyPSA (ready)
- 0078 Internal consistency checks (doing)
- 0079 Source URL verification (ready)
- 0081 Headline F1 replicates (ready)
- 0082 Three-way reference reconciliation (ready)
- 0083 Multiple comparison correction (doing)
- 0084 Temperature control (doing)
- 0085 International classifications mapping (ready)
- 0086 Article scope caveats (ready)

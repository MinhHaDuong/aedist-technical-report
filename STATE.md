Last updated: 2026-04-28T00:00Z (housekeeping: committed dirty files, 3 commits ahead of origin)

## Status

Pipeline end-to-end. Benchmark: 57 models, headline F1 macro-wired (`\HeadlineMeanFOne`, deepseek-v3.2/rag_per_fuel, n=4 runs). CI: 1128 passing, 1 skipped, 1 xfailed. `make lint` now includes ruff + ticket structure check.

**2026-04-25 housekeeping:** Deleted stale branch `worktree-healthcheck`; updated README.md (32→49 models, 52→49 registry, 61→68 tests); updated models.yaml header (46→49 instances).

**2026-04-24:** Full namespace audit completed (epic 0069, 7 tickets, PRs #286–#291): method values migrated, sweep/modelset keys renamed, query modules renamed to call-pattern axis, output dirs renamed, report labels updated, tickets/memory audited. Also: ticket log-placement validator added (`scripts/check_ticket_structure.py`, PR #292), 10 historical tickets fixed.

**Previous session (2026-04-24, morning):** Orphaned worktrees/branches cleaned, stale .wip files cleared, diverged main reconciled.

**2026-04-23:** Census chart moved; v1 architecture slide added; N-plants charts redesigned as horizontal scatter; quality ladder slides inserted (PR #285).

## Blockers

None.

## Next actions

1. **Slides direct editing** — user will edit slides.tex directly (loanwords, STANAG, Watcher mapping, footnote attributions per REVIEW MINOR comments).
2. **Launch ablation Phase 1** — `--seed 42 --provider DeepSeek --temperature 0.0`, 2 pilot reps on base prompt, verify determinism.
3. **Ticket 0102** — escalation-rate decay verification (post-talk).

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: 4 quality criteria (Grounding/Auditability/Freshness/Confidence) — each slide section lifts one criterion.
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.

## Follow-on milestone: Journal submission

- [x] RAG scaling curve: two families, edge-to-cloud (ticket 0021, PR #240)
- [x] Coherence checks + statistical rigor fixes (PR #239)
- [x] Headline F1 replicates: 98.8% → 89.8% mean with CI (ticket 0081)
- [x] Source citation audit: calibration table (ticket 0079)
- [x] Article scope caveats: G10-G13 (ticket 0086)
- [x] Decomposition hallucination fix evaluation (ticket 0068, PR #241)
- [x] Internal coherence measured and reported (ticket 0078, PR #243)
- [x] FDR + ANOVA diagnostics tested (ticket 0083, PR #242)
- [x] Temperature control enforced + limitation documented (ticket 0084, PR #244)
- [x] Phase 2 ablation: 16 prompts on RAG regime (ticket 0088, PR #250) — **invalidated (T=null); rerun planned**
- [x] Multi-agent verification: negative result, dead end (ticket 0059, PR #246)
- [x] Three-way reference reconciliation (ticket 0082, PR #249)
- [x] International classifications mapping (ticket 0085, PR #248)
- [x] Ablation visualization: strip plot + heatmap (ticket 0067, PR #247)
- [x] RAG nondeterminism root-caused: web_search injection (ticket 0094, PR #257)
- [x] Slides temperature caveat (ticket 0093, PR #260)
- [x] Ablation temperature limitation documented, re-run deferred (ticket 0095, PR #259)
- [x] DeepSeek over-context tool_calls behavior documented (ticket 0096)
- [x] §2 Related Work: 4 paragraphs, 15 citations (ticket 0077, PR #273)
- [x] Headline F1 macro-wired: no hardcoded numbers in slides (PR #274)
- [x] Ablation redesign: 7 modules, 18 prompts, 4 regimes, 4 phases (PR #279)
- [x] Source-grounding table wired into report (ticket 0097, PR #280+)
- [x] Ch.3/Ch.6 synced to v0 pipeline design — fusion primitive, 3-tier verification (ticket 0098)
- [x] `verification_methods.tex` rewritten for 3-tier audit-verified, French (ticket 0099, PR #284)
- [x] French slides, all 18 frames, Freshness filled with real F1 data (ticket 0100, PR #281)
- [x] Incrementality probe: growth curve script + 36-call real run (ticket 0101, PR #280)
- [x] Conflict-resolution policy: 6 fixtures, 8 tests (ticket 0104, PR #282)
- [x] Coherence verification script (ticket 0103, PR #282)
- [x] Fusion worker integration: Method.FUSION, query_fusion CLI (ticket 0115, PR #283)
- [x] v1 prototype: incremental fusion loop, 18 iterations master+doc_i (ticket 0076, PR #278)
- [x] Full namespace audit: method values, sweep names, prompts, query modules, output dirs, report labels (tickets 0120-0126, epic 0069, PRs #286-#291)
- [x] Ticket log-placement validator + 10-ticket batch fix (ticket 0127, PR #292)
- [ ] Source-grounding verification Phases 2+3 — full audit (tickets 0118-0119, post-talk)
- [ ] Escalation-rate decay verification (ticket 0102, post-talk)
- [ ] DSPy/MIPROv2 prompt optimization prototype (ticket 0075, post-talk)

## Non-closed tickets (4)

- 0075 DSPy/MIPROv2 prompt optimization — survey done (PR #276); prototype deferred post-talk
- 0102 Verify escalation-rate decay × system (post-talk, blocked by 0097 Phases 2+3)
- 0118 Source-grounding Phase 2 — LLM adjudication (post-talk)
- 0119 Source-grounding Phase 3 — HITL memory (post-talk, blocked by 0118)

Last updated: 2026-04-22 (session: PR #279 open — ablation redesign + slides restructuring)

## Status

Pipeline end-to-end. Benchmark: 37 models, headline F1 macro-wired (`\HeadlineMeanFOne`, deepseek-v3.2/decomposed, n=4 runs). CI: 1078 passing, 2 golden-value skips. §2 Related Work complete (PR #273).

**This session (2026-04-22):** PR #279 open (not yet merged):
- Ablation experiment redesigned: 7 modules (P/O/N/B/T/Sₜ/S_g), 18 prompts (4 anchors + 7 composition + 7 ablation), 4 information regimes (parametric/RAG/web/incremental), 4 phases (Phase 0 DSPy, Phase 1 pilot 2 reps, Phase 2 full, Phase 3 incremental). Previous Phase 2 results invalidated (all T=null). Sourçage split into Sₜ (trace/recall) and S_g (ground/precision).
- Slides restructured around 4 quality criteria: Grounding (van Fraassen), Auditability (Popper), Freshness (incremental fusion), Confidence (3-tier verification). New frame slide added anchored in philosophy of science. Union vote and decomposition demoted: footnote lines in slides, Pitfalls section stub in report.
- `tab_source_grounding.tex` untracked (ticket 0097 Phase 1 artefact) — commit when 0097 advances.

## Blockers

- **F1 drift flag**: `test_decomposed_deepseek_has_ci` reports 0.930 vs expected 0.898; run `make measurements` to check if headline changed.
- **Ablation campaign not launched**: reactive-prancing-shell has `--seed`/`--provider`/`--temperature` flags ready. Must verify determinism (2 pilot reps) before full run.
- **Freshness slide**: placeholder only — needs prototype_v1 results (F1 vs docs-added curve).

## Next actions

1. **Merge PR #279** — ablation redesign + slides restructuring.
2. **Launch ablation Phase 1** from reactive-prancing-shell: `--seed 42 --provider DeepSeek --temperature 0.0`, 2 pilot reps on base prompt, verify identical → then Phase 2 (18 prompts × 4 regimes, 1 rep if deterministic).
3. **Ticket 0100** — finalize French slides (deadline 2026-05-27). Fill Freshness slide when prototype_v1 results available.
4. **Ticket 0097** Phases 2+3 — source grounding audit; blocked until post-talk.
5. **Ticket 0076** — v1 prototype: incremental fusion loop (master + doc_i → master', 18 iterations).

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: 4 quality criteria (Grounding/Auditability/Freshness/Confidence) — each slide section lifts one criterion.
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference. Narrative will follow what worked in the slides.

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
- [ ] Source-grounding verification, 3-tier audit-verified (ticket 0097)
- [ ] Technical report Ch. 6 + Ch. 3 sync to v0 pipeline design (ticket 0098)
- [ ] `verification_methods.tex` rewrite for 3-tier audit-verified (ticket 0099)

## Open tickets (11)

- 0069 Project namespace audit (pending — awaiting external input)
- 0075 DSPy/MIPROv2 prompt optimization — survey done (PR #276); prototype deferred to Phase 0 of ablation campaign
- 0076 v1 prototype: incremental fusion loop, 18 iterations master+doc_i (ready)
- 0097 Verify source-grounding of the master table — Phase 1 done; Phases 2+3 post-talk
- 0098 Report Ch. 6 + Ch. 3 sync to v0 pipeline design (blocked by 0097 full close)
- 0099 Rewrite `verification_methods.tex` for 3-tier audit-verified (blocked by 0097 full close)
- 0100 Finalize Econom'IA 2026 slides — French + layout (deadline 2026-05-27)
- 0101 Verify incrementality × method (soft-blocked on v0 fusion prototype)
- 0102 Verify escalation-rate decay × system (blocked by 0097 Phase 2+3)
- 0103 Verify internal coherence × table (soft-blocked on v0 fusion prototype)
- 0104 Verify conflict-resolution × method (soft-blocked on v0 fusion prototype)

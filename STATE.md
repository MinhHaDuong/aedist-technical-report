Last updated: 2026-05-05T22:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: 4 quality criteria (Grounding/Auditability/Freshness/Confidence) — each slide section lifts one criterion.
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.

## Status

Pipeline end-to-end. Benchmark: 57 models, headline F1 macro-wired (`\HeadlineMeanFOne`, deepseek-v3.2/rag_per_fuel, n=4 runs). CI: 1150 passing, 1 skipped, 2 xfailed. `make lint` includes ruff + ticket structure check.

**Deep-research hypothesis H1 (reformulated, 2026-05-05):** See `docs/experiment-roadmap.md`. H1 requires all four: (a) F1 ≥ 0.988, (b) source-grounding ≥ 80%, (c) no truncation, (d) statistical coherence.

**2026-05-05:** Raid on ticket 0163 complete (PR #327). F1=0.000 mystery solved: GPT-5.4 + Grok 4.20 refused; Ernie 4.5 Thinking produced aggregate tables (no per-plant inventory). Evaluator is correct. Regression tests added (`tests/test_evaluator_robustness.py`). Output token ceiling raised 32K→64K (Claude Opus was at 31K/32K). Experiment roadmap written (`docs/experiment-roadmap.md`).

**erg v2 migration (2026-05-05):** 126 closed tickets auto-archived to `tickets/closed/` by new erg binary. Open count: 25.

## Blockers

- **0139** (seed + finish_reason in RunRecord) should be resolved before Phase 3 full runs. Workaround for Phase 1 pilots: grep finish_reason from raw JSON manually.
- **0150** OSF preregistration — human action, ~20 min, form at `docs/preregistration-osf.md`. Must precede full runs for confirmatory claim.

## Priorities (2026-05-05)

1. **Phase 0 gate**: 0164 price audit + 0150 OSF registration → unlock Phase 1 pilots.
2. **Phase 1 pilots** (~$5–10): 3 frontier cloud models × `prompt_complete` × 3 reps. Check finish_reason, row count, F1 after each run.
3. **0139 JobSpec**: add seed, provider_order, finish_reason to RunRecord — needed before Phase 3 full runs.
4. **Prompt meta-review** by 3 SOTA agents (Claude Opus 4.6, DeepSeek R1, + 1) — needs go-ahead.
5. **Slides update** for H1 reformulation (4-criteria, not just F1).

## Benchmark-wide F1 leaderboard (2026-04-30, 327 records)

**Nobody hits F1 = 1.0.** Top:

| F1     | Method              | Model                              | Note |
|--------|---------------------|------------------------------------|------|
| 0.988  | decomposed RAG      | DeepSeek V3.2                      | headline mean n=4: 0.898 |
| 0.984  | direct (parametric) | qwen3.5:9b (local)                 | n=1, needs confirmation |
| 0.982  | multiturn / verification | Claude Opus 4.6               |      |
| 0.975  | decomposed          | Gemini 2.5 Flash Lite              |      |
| 0.968  | RAG wholesale       | Qwen 3.5 122B                      |      |

**`direct_complete` arm:** best F1 = 0.557 (n=9, excl. 3 non-attempts). Three frontier models failed: 2 refusals (GPT-5.4, Grok 4.20), 1 format error (Ernie 4.5 Thinking — aggregate tables only). Evaluator confirmed correct.

## Open tickets (25)

- 0075 DSPy/MIPROv2 autoresearch — post-talk
- 0102 Verify escalation-rate decay — post-talk, blocked by missing fusion+HITL
- 0118 Source-grounding Phase 2 — LLM adjudication, post-talk
- 0119 Source-grounding Phase 3 — HITL memory, blocked by 0118
- 0133 Pareto scatter Python PDF
- 0134 Regimes scatter — local sweep in flight on padme tmux `regimes-fill`
- 0135 Regimes scatter visual tuning — blocked by 0134
- 0138 No-Think confound audit
- **0139** JobSpec: seed + provider_order + finish_reason in RunRecord *(Phase 0 gate)*
- 0140 Split Makefile by workpackage
- 0143 Rerun ablation with verbatim modules — unblocked (0142 merged)
- 0144 RAG+reasoning coherence cell — blocked by 0139
- 0146 Capability timeline expand and figure
- 0149 Extract main results and hypotheses — open PR #316
- **0150** Preregister hypotheses *(pending human, Phase 0 gate)*
- 0151 Literature review against argument
- 0152 Align slides on argument
- 0153 Redesign experiments along argument
- 0154 Run redesigned experiments — blocked by 0153
- 0157 figures.toml ordered modelsets
- 0158 Structured prompt modules/modalities taxonomy
- 0159 Capability evaluation 8 dimensions
- 0160 Claude Code CLI route adapter
- 0162 Model-set dispatch smoke test
- **0164** Model registry price audit *(Phase 0 gate — run before any sweep >$10)*

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
- [x] Ablation: citation_columns / sourcing_ground split, MoE repeat=3 fixed (PR #295)
- [x] Slides pgfplots-free: census scatter (ticket 0131, PR #296), regimes scatter (ticket 0132, PR #297)
- [x] Regimes scatter cloud sweep (ticket 0134, Hy3 preview free + qwen3.6-35b-a3b, $0.52)
- [x] Model instance registry: Python migration complete (tickets 0156/0161, PR #326)
- [x] Evaluator confirmed correct: F1=0.000 = refusals/format errors, not parser bug (ticket 0163, PR #327)
- [ ] Regimes scatter local sweep (ticket 0134, in flight on padme tmux `regimes-fill`)
- [ ] Regimes scatter visual tuning (ticket 0135, blocked by 0134)
- [ ] Pareto scatter Python PDF (ticket 0133, pending)
- [ ] Slides narrative restructure (ticket 0129)
- [ ] H1 pilot runs: 3 frontier models × prompt_complete × 3 reps (Phase 1, ~$5-10)
- [ ] Source-grounding verification Phases 2+3 — full audit (tickets 0118-0119, post-talk)
- [ ] Escalation-rate decay verification (ticket 0102, post-talk)
- [ ] DSPy/MIPROv2 prompt optimization prototype (ticket 0075, post-talk)

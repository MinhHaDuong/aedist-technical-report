Last updated: 2026-05-10T09:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: four quality properties (Accuracy, Coherence, Provenance, Temporality) — each rung of the method ladder lifts one limit.
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.

## Status

Pipeline end-to-end. Benchmark: 57 models, headline F1 macro-wired (`\HeadlineMeanFOne`, deepseek-v3.2/rag_per_fuel, n=4 runs). CI: 1150 passing, 1 skipped, 2 xfailed. `make lint` includes ruff + ticket structure check.

**Argument arc (2026-05-06, finalized):** `docs/synopsis.md` locked. Four quality properties: Accuracy, Coherence, Provenance, Temporality. Four method-ladder limits: Articulation, Coverage, Freshness, Coherence (Provenance unaddressed by any rung). H1–H4 confirmatory hypotheses formulated and registered in `docs/hypotheses.md` and `docs/preregistration-osf.md`.

**H1–H4 (2026-05-06):**
- **H1** (Articulation rung): multi-turn adds measurable F1 over direct; paired ΔF1 ≥ 0.03, p < 0.05
- **H2** (Coverage rung): RAG adds measurable F1 over multi-turn; same decision rule
- **H3** (accuracy–provenance trade-off): single parametric prompt does not simultaneously achieve full recall and verifiable per-row attribution; ΔF1(complete−extract) < −0.10 AND citation validity < 0.50
- **H4** (local approaches frontier): qwen3.5:122b on A4000 GPU within 0.05 F1 of cloud frontier ceiling (0.988)

**Phase 0 gates (2026-05-06):** 0163 ✓ (evaluator correct), 0164 ✓ (price audit), 0150 pending human (~20 min).

**Prompt fixes (2026-05-06):** `prompt_complete.txt` + module files updated: lifecycle scope broadened (proposed→dismantled), count hint removed, LOW-confidence tiebreaker added.

## Blockers

- **0150** OSF preregistration — human action, ~20 min, form at `docs/preregistration-osf.md`. **Must precede all confirmatory sweep runs.**
- **0139** (seed + finish_reason in RunRecord) needed before Phase 3 full runs. Workaround for Phase 1: grep finish_reason from raw JSON manually.

## Priorities (2026-05-06)

1. **0150 OSF preregistration** — human action, unblocks all confirmatory runs.
2. **Phase 1 pilots** (~$2–5): 5 matched frontier models × `prompt_extract` × 3 conditions × 3 reps. Verify finish_reason, row count, F1.
3. **Phase 2 H3 sweep** (~$5–10): 5 models × `prompt_complete_no_web` × 3 reps (Condition A shared with Phase 1 direct).
4. **0165 prompt module–aspect mapping** — design ablation with modules targeting property aspects.
5. **0139 JobSpec** — add seed, provider_order, finish_reason to RunRecord.

## Benchmark-wide F1 leaderboard (2026-04-30, 327 records)

**Nobody hits F1 = 1.0.** Top:

| F1     | Method              | Model                              | Note |
|--------|---------------------|------------------------------------|------|
| 0.988  | decomposed RAG      | DeepSeek V3.2                      | headline mean n=4: 0.898 |
| 0.984  | direct (parametric) | qwen3.5:9b (local)                 | n=1, needs confirmation |
| 0.982  | multiturn / verification | Claude Opus 4.6               |      |
| 0.975  | decomposed          | Gemini 2.5 Flash Lite              |      |
| 0.968  | RAG wholesale       | Qwen 3.5 122B                      |      |

**`direct_complete` arm:** best F1 = 0.557 (n=9, excl. 3 non-attempts). Three frontier models failed: 2 refusals (GPT-5.4, Grok 4.20), 1 format error (Ernie 4.5 Thinking — aggregate tables only). Evaluator confirmed correct (ticket 0163).

## Open tickets (22)

- 0075 DSPy/MIPROv2 autoresearch — post-talk
- 0102 Verify escalation-rate decay — post-talk, blocked by missing fusion+HITL
- 0118 Source-grounding Phase 2 — LLM adjudication, post-talk
- 0119 Source-grounding Phase 3 — HITL memory, blocked by 0118
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
- 0158 Structured prompt modules/modalities taxonomy
- 0159 Capability evaluation 8 dimensions
- 0160 Claude Code CLI route adapter
- **0165** Prompt module–aspect mapping *(design ablation, unblocked)*

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
- [x] Model registry price audit: 6 prices updated >10%, 1 model retired (ticket 0164, 2026-05-06)
- [x] H1–H4 hypothesis set finalized: synopsis.md + hypotheses.md + preregistration-osf.md + roadmap (2026-05-06)
- [ ] Regimes scatter local sweep (ticket 0134, in flight on padme tmux `regimes-fill`)
- [ ] Regimes scatter visual tuning (ticket 0135, blocked by 0134)
- [ ] Pareto scatter Python PDF (ticket 0133, pending)
- [ ] Phase 1 sweeps: H1/H2 ladder (5 models × 3 conditions × 3 reps, ~$2-5, blocked by OSF gate)
- [ ] Phase 2 sweeps: H3 parametric attribution (5 models × 2 conditions × 3 reps, ~$5-10, blocked by OSF gate)
- [ ] Source-grounding verification Phases 2+3 — full audit (tickets 0118-0119, post-talk)
- [ ] Escalation-rate decay verification (ticket 0102, post-talk)
- [ ] DSPy/MIPROv2 prompt optimization prototype (ticket 0075, post-talk)

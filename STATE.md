Last updated: 2026-04-30T17:00Z

## Status

Pipeline end-to-end. Benchmark: 57 models, headline F1 macro-wired (`\HeadlineMeanFOne`, deepseek-v3.2/rag_per_fuel, n=4 runs). CI: 1135 passing, 1 skipped, 2 xfailed. `make lint` includes ruff + ticket structure check.

**2026-04-30 (today):** Regimes scatter ticket 0134 pivoted to free Hy3 preview top-end (drops paid GPT-5.5; expires 2026-05-08). Cloud sweeps complete (Hy3 + qwen3.6-35b-a3b × direct/multiturn/RAG, $0.52). Local sweeps running in padme tmux `regimes-fill` (qwen3.6:35b + ministral-3:14b + qwen3.5:9b × 3 methods); patched `query_direct.py` and `query_multiturn.py` to use Ollama native `/api/chat` for `num_ctx` (commits `d27c393`, `031cef2`); added `message.thinking` capture in record JSONs (commit `f379c57`). Measurement-framework note `docs/measurement-framework.md` written (axes vs lenses, four limits Articulation/Coverage/Coherence/Freshness). Tickets 0140 (Makefile split), 0141 (registry providers-block refactor), 0142 (rewrite ablation modules verbatim from prompt_complete), 0143 (rerun ablation, blocks on 0142). API-key leak via `ps -ef` discovered + remediated: `~/.claude/scripts/on-start.sh` no longer persists `.env` (`d4653eb`); AEDIST Makefile centralized on `$(UV_RUN) := uv run --project .. --env-file ../.env` (`4000c21`); 5 follow-up tickets opened in Oeconomia / chemin-de-voix / Fuzzy Corpus / Cadens / maiba.

**2026-04-29:** Slides fully pgfplots-free: census scatter (ticket 0131, PR #296) and regimes scatter (ticket 0132) replaced with Python PDF figures. Ablation module split: `citation_columns` + `sourcing_ground`, MoE repeat=3 fixed (PR #295).

**2026-04-24:** Full namespace audit completed (epic 0069, 7 tickets, PRs #286–#291).

## Blockers

None.

## Priorities (operator, set 2026-04-30)

1. **Align ablation and prompt_complete.** Tickets 0142 (rewrite ablation modules as verbatim paragraph extractions from `prompts/prompt_complete.txt`) → 0143 (rerun ablation, blocked-by 0142). Today's modules are conceptually similar but not literal; 0142's exit gate is a `diff` between assembled-modules-composite and `prompt_complete.txt`.
2. **Verify `prompt_complete` reaches F1 = 1 across multiple runs and models.** Current state of `outputs/direct_complete` (n=1 per model, 12 models): **best F1 = 0.557 (GLM-5 Turbo); none at 1.0; three at 0.000 (Ernie 4.5, GPT-5.4, Grok 4.20).** Mean ≈ 0.35. Consequence: the deep-research arm does not yet ceiling the regimes scatter — verify what's broken (extraction parsing? reference mismatch? actual model failure?) before claiming joint stages-3+4 contribution.
3. **Set up at least one local model with deep-research capability** (web search + reasoning) to run `prompt_complete` to F1 = 1 consistently — overnight is fine. Dev phase: **coal-only subset** of the reference table, not the full thermal inventory. Candidate path: a thinking-capable Ollama model + Tavily/web wrapper + tool-use loop, or a deepagents-style runner (per ticket 0076's evaluation).

## Benchmark-wide F1 leaderboard (2026-04-30, 327 records scanned)

**Nobody hits F1 = 1.0.** Top of the leaderboard:

| F1     | Method              | Model                              | Note |
|--------|---------------------|------------------------------------|------|
| 0.988  | decomposed RAG      | DeepSeek V3.2                      | Best-of-runs; the headline `\HeadlineMeanFOne` mean across n=4 is 0.898 |
| 0.984  | direct (parametric) | **qwen3.5:9b (local)**             | 9B local model on direct extraction — beats most cloud frontier |
| 0.982  | multiturn / verification | Claude Opus 4.6                |      |
| 0.975  | decomposed          | Gemini 2.5 Flash Lite              |      |
| 0.968  | RAG wholesale       | Qwen 3.5 122B                      |      |

Two findings worth weighting against the priorities:

- **The deep-research arm is BELOW the regimes-scatter ceiling.** Best `direct_complete` = 0.557 vs. best benchmark-wide = 0.988. Stages 3+4 (Coherence + Freshness) appear to *lower* extraction F1 in current data — opposite of the assumed narrative arc. **Three `0.000` rows in `direct_complete` (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20)** are very suspicious for capable models — likely an evaluator parse failure on the structured-document output, not actual model failure. **Diagnose this before any priority-3 build**, because if the parser is broken on `prompt_complete` outputs, F1 = 1 is unreachable by construction.
- **qwen3.5:9b at 0.984 on direct (n=1)** partially answers priority 3 already — a small local model is near-ceiling without tools / web / reasoning. Verify with repeats on coal-only before banking on it. If real, priority 3 may collapse to "use this 9B as the local extractor" rather than "build a deep-research stack".

Quick wins for the return session:
1. Read one of the `0.000` `direct_complete` records (e.g. `gpt-5.4-run1.record.json`) alongside its `.json` — confirm whether the response contained a valid table the parser missed.
2. Run qwen3.5:9b/direct ×3 on the coal-only reference to confirm 0.984 reproduces.
3. Then decide whether priority 3 is "build deep-research locally" or "verify the 9B and ship".

## Non-closed tickets (15)

- 0075 DSPy/MIPROv2 — pending, deferred post-talk
- 0102 Verify escalation-rate decay (post-talk, blocked by missing v0 fusion + HITL memory)
- 0118 Source-grounding Phase 2 — LLM adjudication (post-talk, gate 2026-05-27)
- 0119 Source-grounding Phase 3 — HITL memory (post-talk, blocked by 0118)
- 0129 Slides narrative restructure (5-act arc)
- 0133 Pareto scatter Python PDF — pending, deferred (after 0134)
- 0134 Regimes scatter — pivoted to Hy3 preview free; cloud done, local in flight on padme
- 0135 Regimes scatter visual tuning — blocked by 0134
- 0136 Regimes scatter local 30B — qwen3.6:35b in registry
- 0137 Regimes scatter local 8B
- 0139 JobSpec missing API params (seed, provider_order, max_tokens, num_ctx, finish_reason)
- 0140 Split Makefile by workpackage
- 0141 Registry refactor — one entry per logical model with providers sub-block
- 0142 Rewrite ablation modules verbatim from prompt_complete (priority 1)
- 0143 Rerun ablation with verbatim modules (blocked-by 0142)

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
- [x] Ablation: citation_columns / sourcing_ground split, MoE repeat=3 fixed (PR #295)
- [x] Slides pgfplots-free: census scatter (ticket 0131, PR #296), regimes scatter (ticket 0132, PR #297)
- [x] Regimes scatter cloud sweep (ticket 0134, Hy3 preview free + qwen3.6-35b-a3b, $0.52)
- [ ] Regimes scatter local sweep (ticket 0134, in flight on padme tmux `regimes-fill`)
- [ ] Regimes scatter visual tuning (ticket 0135, blocked by 0134)
- [ ] Pareto scatter Python PDF (ticket 0133, pending)
- [ ] Slides narrative restructure (ticket 0129)
- [ ] Verify prompt_complete reaches F1 = 1 (priority 2)
- [ ] Local deep-research model for prompt_complete F1 = 1 on coal-only (priority 3)
- [ ] Source-grounding verification Phases 2+3 — full audit (tickets 0118-0119, post-talk)
- [ ] Escalation-rate decay verification (ticket 0102, post-talk)
- [ ] DSPy/MIPROv2 prompt optimization prototype (ticket 0075, post-talk)

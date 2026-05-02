Last updated: 2026-05-02T14:30Z

## Status

Pipeline end-to-end. Benchmark: 57 models, headline F1 macro-wired (`\HeadlineMeanFOne`, deepseek-v3.2/rag_per_fuel, n=4 runs). CI: 1142 passing, 1 skipped, 2 xfailed. `make lint` includes ruff + ticket structure check.

**2026-05-01 (today):** Opened 5 tickets for experiment infrastructure redesign:
- **0156** Model instance registry: `name`/`display_name`/`route`/`base_url`/`model_id` schema. Adds `route` enum (openrouter, ollama, openllm, claude-code-cli, codex). Supersedes 0141.
- **0157** `figures.toml` with ordered named modelsets (`frontier`, `full`, `ablation`). Blocked by 0156.
- **0158** Structured prompt taxonomy: modules (persona, goal, scope, information, context, constraint) × modalities. Frames multi-turn as temporal decomposition. Independent.
- **0159** Formal capability evaluation: 8 dimensions (arithmetic, general knowledge, reasoning, web search, multilingual, energy, statistics, geography), ordinal 0–3 scores. Blocked by 0156.
- **0160** Claude Code CLI route adapter (`claude --print --model`). Blocked by 0156.

All 6 local branches pushed to origin. Tests green.

**2026-04-30:** Regimes scatter (ticket 0134) pivoted to free Hy3 preview; cloud sweeps complete ($0.52). Argument note `docs/argument.md` written (four limits Articulation/Coverage/Coherence/Freshness). Tickets 0147–0155 opened and progressed. API-key leak via `ps -ef` remediated.

**2026-04-29:** Slides fully pgfplots-free. Ablation module split MoE repeat=3 fixed (PR #295).

## Blockers

None.

## Priorities (set 2026-04-30, confirmed 2026-05-01)

1. **Align ablation and prompt_complete.** Ticket 0142 (rewrite ablation modules verbatim from `prompt_complete.txt`) → 0143 (rerun). Exit gate: `diff` assembled-composite vs `prompt_complete.txt` = 0.
2. **Diagnose `direct_complete` F1 = 0.000 rows.** Three capable models (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20) score zero — almost certainly a parser failure on structured-document output. Read one raw `.record.json` + confirm before any priority-3 build. If parser is broken, F1 = 1 is unreachable by construction.
3. **Verify qwen3.5:9b/direct ×3 on coal-only.** Single-run F1 = 0.984 on direct is remarkable; confirm with repeats before deciding whether priority-3 reduces to "use this 9B" vs "build deep-research stack".
4. **Registry / figures infrastructure (new, 0156→0160).** Blocked only by implementation order: 0156 first, then 0157/0159/0160 in parallel.

## Benchmark-wide F1 leaderboard (2026-04-30, 327 records)

**Nobody hits F1 = 1.0.** Top:

| F1     | Method              | Model                              | Note |
|--------|---------------------|------------------------------------|------|
| 0.988  | decomposed RAG      | DeepSeek V3.2                      | headline mean n=4: 0.898 |
| 0.984  | direct (parametric) | qwen3.5:9b (local)                 | n=1, needs confirmation |
| 0.982  | multiturn / verification | Claude Opus 4.6               |      |
| 0.975  | decomposed          | Gemini 2.5 Flash Lite              |      |
| 0.968  | RAG wholesale       | Qwen 3.5 122B                      |      |

**Deep-research arm BELOW regimes-scatter ceiling:** best `direct_complete` = 0.557 vs benchmark-wide = 0.988. Stages 3+4 currently lower F1 — diagnose parser before building further.

## Open tickets (22 open, 3 pending)

- 0075 DSPy/MIPROv2 — pending, post-talk
- 0102 Verify escalation-rate decay — post-talk, blocked by missing v0 fusion + HITL memory
- 0118 Source-grounding Phase 2 — LLM adjudication, post-talk, gate 2026-05-27
- 0119 Source-grounding Phase 3 — HITL memory, blocked by 0118
- 0133 Pareto scatter Python PDF — deferred, after 0134
- 0134 Regimes scatter — cloud done, local in flight on padme tmux `regimes-fill`
- 0135 Regimes scatter visual tuning — blocked by 0134
- 0138 Audit experiment parameter confounds; fix missing fields in JobSpec/RunRecord
- 0139 JobSpec missing API params (seed, provider_order, max_tokens, num_ctx, finish_reason)
- 0140 Split Makefile by workpackage
- 0141 Registry refactor — one entry per model, providers as sub-block (superseded by 0156)
- 0142 Rewrite ablation modules verbatim from prompt_complete **(priority 1)**
- 0143 Rerun ablation with verbatim modules — blocked by 0142
- 0144 Add RAG + reasoning cell (no web) to isolate Coherence delta
- 0146 Capability timeline expand and figure
- 0150 Preregister confirmatory hypotheses on OSF — pending review
- 0151 Conduct literature review against the argument
- 0152 Align slides on the argument's three-part structure
- 0153 Redesign experiments along the argument's hypotheses
- 0154 Run the redesigned experiments and record verdicts
- 0156 Model instance registry (name/display_name/route/base_url/model_id)
- 0157 figures.toml ordered modelsets — blocked by 0156
- 0158 Structured prompt modules/modalities taxonomy
- 0159 Capability evaluation 8 dimensions — blocked by 0156
- 0160 Claude Code CLI route adapter — blocked by 0156

## Stale worktrees (review needed)

- `verify-315`: detached HEAD, no associated open ticket — investigate and remove.
- `/tmp/wt-slides-0129`: ticket 0129 closed — check if any work needs merging, then delete.
- `.claude/worktrees/raid-0142`: ticket 0142 closed (PRs #313/#319/#320 merged) — safe to remove.

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

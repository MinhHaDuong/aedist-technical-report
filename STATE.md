Last updated: 2026-05-20T22:10Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: four quality properties (Accuracy, Coherence, Provenance, Temporality) — each rung of the method ladder lifts one limit.
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.

## Current goal:

Complete exploratory research, freeze the argument and the slides story.

## Workplan (set 2026-05-15)

1. **Experiment 1 baseline re-sweep (ticket chain 0174–0178).** Branch `t0174-exp1-baseline` pushed, pending review. Unblocked now: **0175** (lock design — update harness.py _MODULE_ORDER, modules/README.md, experiments.toml, Annex A) and **0176** (reference provenance — write PROVENANCE.md + manuscript paragraph). Blocked: 0177 (45-run sweep) on 0175; 0178 (update manuscript) on 0177.
2. **Implement the SOTA experiment (slides §4 — Falsify H0: Deep research agents are enough).** Umbrella **0166**, four SOTA agents (Anthropic Opus 4.6 / OpenAI GPT-5.5 / Mistral Large 2512 / Qwen3-Max via DashScope).
   - **Wave 1 (done, PR #331):** ticket 0172 — RunRecord schema extension.
   - **Wave 2 (DONE 2026-05-20, PRs #350/#351/#353/#352):** tickets 0167/0168/0169/0173 — four direct-API adapters merged. All 4 live smokes recorded ($0.235 total / cap $2.00, 49 citations across the wave). Adapter surface inconsistency to flag for Phase A (0170): Anthropic exposes `dispatch`+`main`; the 3 others expose `build_request`/`parse_response`/`run`.
   - **Next: ticket 0185 (interactive smoke for Exp 2)** — author-gated PRESS-SPACE walkthrough of Phase A+B on one agent at a time, starting Mistral (cheapest at $0.025 baseline). Validates meta-prompt + designed prompt + Phase B response before automating via 0170.
   - **Wave 3:** tickets 0170 (Phase A harness) + 0171 (Phase C cross-eval rubric, 0-3 anchored). 0170 informed by 0185 traces.
   - **Phase B (queries):** after Wave 3 + 0185 validation. Budget cap ~$140 total.
   - **Follow-ups from Wave 2:** 0186 (`erg next-id` cross-worktree fix), 0187 (Qwen adapter: ADR-7 method_params + cost cap default + dashscope pin).
3. Implement the prototype described in synopsis (the stateful-agentic v1, synopsis §5). Not yet ticketed; opens after Wave 3 lands and Phase B has run.

## Backlog
1. **Diagnose `direct_complete` F1 = 0.000 rows.** Three capable models (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20) score zero — almost certainly a parser failure on structured-document output. Read one raw `.record.json` + confirm before any priority-3 build. If parser is broken, F1 = 1 is unreachable by construction.
2. **Verify qwen3.5:9b/direct ×3 on coal-only.** Single-run F1 = 0.984 on direct is remarkable; confirm with repeats before deciding whether priority-3 reduces to "use this 9B" vs "build deep-research stack".
3. **Registry / figures infrastructure (new, 0156→0160).** Blocked only by implementation order: 0156 first, then 0157/0159/0160 in parallel.

## Suspended / deferred

**Rerun ablation with verbatim modules.** Ticket 0142 closed (PR #313). Ticket 0143 (rerun) now unblocked. Exit gate: `diff` assembled-composite vs `prompt_complete.txt` = 0 (verified).

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.




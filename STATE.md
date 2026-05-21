Last updated: 2026-05-21T00:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: four quality properties (Accuracy, Coherence, Provenance, Temporality) — each rung of the method ladder lifts one limit.
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

## Current goal

Land Exp 1 results in the manuscript; freeze the slides story by 2026-05-26.

## Workplan

1. **Experiment 1 — DONE.** Tickets 0174→0177 + follow-ups 0179/0181/0182/0183/0184 all closed. Final journal-v2 lineup: 16 models × 5 reps = 80 rows in `experiments/outputs/ablation/direct/p1_base/` (77 ok / 3 declined / 0 error / $2.85 total). The 3 declines are all GPT-5.5 — kept as data, semantic refusal of the task's "complete, primary-sourced" framing. Cost summary: `make exp1-cost-summary` (→ `report/inputs/generated/tab_exp1_cost_summary.tex`). **0178 next**: pull F1, refusal, cost numbers into the manuscript's Annex A results section + the H1–H4 discussion.
2. **SOTA experiment (slides §4 — Falsify H0).** Umbrella **0166**, four agents (Opus 4.6 / GPT-5.5 / Mistral Large 2512 / qwen3-max via DashScope).
   - **Wave 1 (done, PR #331):** 0172 RunRecord schema extension.
   - **Wave 2 (done, PRs #350/#351/#352/#353):** 0167/0168/0169/0173 direct-API adapters merged. All 4 live smokes recorded ($0.235 total / cap $2.00, 49 citations across the wave).
   - **Next: 0185** — author-gated interactive smoke (PRESS-SPACE walkthrough of Phase A+B on one agent at a time, starting Mistral at $0.025 baseline). Validates meta-prompt + designed prompt + Phase B response before automating via 0170.
   - **Wave 3:** 0170 (Phase A harness) + 0171 (Phase C cross-eval rubric, 0–3 anchored). 0170 informed by 0185 traces.
   - **Phase B:** after Wave 3 + 0185 validation. Budget cap ~$140 total.
3. Stateful-agentic v1 prototype (synopsis §5). Opens after Wave 3 lands and Phase B has run.

## Backlog (post-conference)

1. **Tooling** — 0179 (refresh prompt_complete.txt), 0186 (`erg next-id` cross-worktree), 0187 (Qwen adapter ADR-7 method_params + cost cap default + dashscope pin), 0143 (rerun ablation with verbatim modules).
2. **Scaling-curve diagnosis** — direct_complete F1=0 on 3 capable models (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20) — likely parser failure on structured-document output. Read one raw `.record.json` before any priority-3 build.
3. **Registry / figures infrastructure** — 0156→0160 implementation order.

## Suspended / deferred

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.

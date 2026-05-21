Last updated: 2026-05-21T11:50Z

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

1. **Experiment 1 — DONE.** Baseline 16×5=80 rows in `outputs/ablation/direct/p1_base/` (77 ok / 3 declined / $2.85) plus topup 16×≤3=43 rows in `p1_base.topup/` (PR #386, ticket 0198) capturing `reasoning_tokens`. 0178 (manuscript Annex A) and 0198 (interday-variability column) both closed. Cost summary: `make exp1-cost-summary`; reasoning table: `make exp1-reasoning-topup`.
2. **SOTA experiment (slides §4 — Falsify H0).** Umbrella **0166**, four agents (Opus 4.6 / GPT-5.5 / Mistral Large 2512 / qwen3-max via DashScope).
   - **Wave 1 (done, PR #331):** 0172 RunRecord schema extension.
   - **Wave 2 (done, PRs #350/#351/#352/#353):** 0167/0168/0169/0173 direct-API adapters merged. All 4 live smokes recorded ($0.235 total / cap $2.00, 49 citations across the wave).
   - **Next: 0185** — author-gated interactive smoke (PRESS-SPACE walkthrough of Phase A+B on one agent at a time, starting Mistral at $0.025 baseline). Validates meta-prompt + designed prompt + Phase B response before automating via 0170.
   - **Wave 3:** 0170 (Phase A harness) + 0171 (Phase C cross-eval rubric, 0–3 anchored). 0170 informed by 0185 traces.
   - **Phase B:** after Wave 3 + 0185 validation. Budget cap ~$140 total.
3. Stateful-agentic v1 prototype (synopsis §5). Opens after Wave 3 lands and Phase B has run.

## Backlog (post-conference)

1. **Tooling** — 0203 (worker exits on 429), 0204 (deepseek-v4-pro null content hangs worker) — both surfaced during the 0198 raid. Raid-skill follow-ups and `erg next-id` cross-worktree re-filed to ~/.claude/tickets and ~/git-erg respectively.
2. **Scaling-curve diagnosis** — direct_complete F1=0 on 3 capable models (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20) — likely parser failure on structured-document output. Read one raw `.record.json` before any priority-3 build.
3. **Registry / figures infrastructure** — 0156→0160 implementation order.

## Suspended / deferred

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.

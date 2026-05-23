Last updated: 2026-05-23T09:30Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27 (5 days)

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: four quality properties (Accuracy, Coherence, Provenance, Temporality) — each rung of the method ladder lifts one limit. Talk now includes Exp 2 optimized arm (decision 2026-05-22).
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

## Current goal

**Complete Exp 2 Phase B-0 re-run**, then full N=5 optimized batch. Slides freeze 2026-05-26.

## Workplan

1. **Experiment 1 — DONE.** 16×5=80 rows, reasoning topup PR #386. Cost summary: `make exp1-cost-summary`.
2. **Experiment 2 — naive arm DONE; optimized arm B-0 re-run pending.**
   - Protocol v3 merged (#428). Tag `exp2-prereg-v1` confirmed on origin/main.
   - Naive arm: all four providers complete (flat layout in `experiments/outputs/sota_exp2_naive_arm/`).
   - Adapter restore in review: PR #437 restores Anthropic + Qwen dispatch tables reverted by #433. Must merge before re-run.
   - **Phase B-0 first attempt (2026-05-23):** OpenAI WARN (162 rows, classifier broken); Qwen WARN (32 rows, token cap hit); Mistral FAIL (Phase A parser — fix in t0237-fg bb0def4); Anthropic FAIL (killed). See `experiments/outputs/sota_exp2_phase_b0/summary.md`.
   - **B-0 re-run TODO** (after #437 merges):
     ```
     uv run python -m experiments.sota.exp2_interactive_smoke \
         --agents mistral anthropic \
         --output-dir experiments/outputs/sota_exp2_phase_b0 \
         --no-confirm
     ```
     OpenAI and Qwen artefacts already exist; accepted as WARN by inspection per §3.5.1.
   - Optimized-arm full N=5 if B-0 passes (ticket 0237).
3. Stateful-agentic v1 prototype (synopsis §5). Opens post-conference.

## Backlog (post-conference)

1. **Tooling** — 0203/0204 raid follow-ups still open.
2. **Scaling-curve diagnosis** — direct_complete F1=0 on 3 capable models; likely parser failure on structured-document output.
3. **Registry / figures infrastructure** — 0156→0160.

## Suspended / deferred

**Paper sequencing**: report stays exploratory. Paper writing opens after slides locked post-conference.

Last updated: 2026-05-23T12:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27 (4 days)

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: four quality properties (Accuracy, Coherence, Provenance, Temporality) — each rung of the method ladder lifts one limit. Talk now includes Exp 2 optimized arm (decision 2026-05-22).
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

## Current goal

**Merge Phase B-0 code PRs, then launch N=5 batch (ticket 0242).**

## Workplan

1. **Experiment 1 — DONE.** 16×5=80 rows, reasoning topup PR #386. Cost summary: `make exp1-cost-summary`.
2. **Experiment 2 — naive arm DONE; optimized arm B-0 gate PASSED.**
   - Phase B-0: all 4 agents classified `report`, total cost $2.72. Ticket 0237 closed.
   - Outputs in `experiments/outputs/sota_exp2_phase_b0/` (consolidated flat layout).
   - **Phase B-full (N=5) next:** ticket 0242 unblocked. Code PRs (branch t0237-fg) pending merge.
   - Launch: `--run-number N --reuse-phase-a-from experiments/outputs/sota_exp2_phase_b0/probes --output-dir experiments/outputs/sota_exp2_phase_b_full`; see ticket 0242 for full commands.
3. Stateful-agentic v1 prototype (synopsis §5). Opens post-conference.

## Backlog (post-conference)

1. **Tooling** — 0203/0204 raid follow-ups still open.
2. **Scaling-curve diagnosis** — direct_complete F1=0 on 3 capable models; likely parser failure on structured-document output.
3. **Registry / figures infrastructure** — 0156→0160.

## Suspended / deferred

**Paper sequencing**: report stays exploratory. Paper writing opens after slides locked post-conference.

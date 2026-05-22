Last updated: 2026-05-22T22:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 — Cergy, 2026-05-27 (5 days)

Conference talk at Thema/Cergy. Deliverable: French slides.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: four quality properties (Accuracy, Coherence, Provenance, Temporality) — each rung of the method ladder lifts one limit. Talk now includes Exp 2 optimized arm (decision 2026-05-22).
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

## Current goal

**Finish OSF pre-registration**, then dispatch both arms (naive + optimized). Slides freeze 2026-05-26.

## Workplan

1. **Experiment 1 — DONE.** 16×5=80 rows, reasoning topup PR #386. Cost summary: `make exp1-cost-summary`.
2. **Experiment 2 — protocol v3 + four-provider adapters all landed.**
   - Protocol v3 merged (#428): six-doc spec + naive arm + §3.5.1 pre-registration plan with H1–H6.
   - Path B adapters merged: #429 OpenAI / #430 Anthropic / #431 Qwen wire each provider into the Phase B multi-turn state machine via the `CALL_FNS` dispatch tables. Mistral was already wired.
   - **OSF pre-registration IN FLIGHT.** First archival failed (third-party files error); user troubleshooting with support@osf.io. Howto at `docs/preregistration-howto.md`.
   - **Next once OSF DOI lands:**
     - Tag commit `exp2-prereg-v1`, push.
     - Naive-arm batch: `uv run python -m experiments.sota.exp2_naive_arm --n 5` (~$20, ~30 min).
     - Optimized-arm Phase B-0 smoke (ticket **0237**, blocked-by closed 0234/0235/0236 — now unblocked).
     - Optimized-arm full N=5 if B-0 passes.
3. Stateful-agentic v1 prototype (synopsis §5). Opens post-conference.

## Backlog (post-conference)

1. **Tooling** — 0203/0204 raid follow-ups still open.
2. **Scaling-curve diagnosis** — direct_complete F1=0 on 3 capable models; likely parser failure on structured-document output.
3. **Registry / figures infrastructure** — 0156→0160.

## Suspended / deferred

**Paper sequencing**: report stays exploratory. Paper writing opens after slides locked post-conference.

Last updated: 2026-05-23T22:30Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 delivery runway

Conference talk at Thema/Cergy. Deliverable: French slides and a coherent Exp 2/3 evidence narrative.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Thesis: four quality properties (Accuracy, Coherence, Provenance, Temporality) — each rung of the method ladder lifts one limit. Talk now includes Exp 2 optimized arm (decision 2026-05-22).
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Homepage: https://economia.sciencesconf.org/

Milestones in order:
1. Experiment 3 runs
2. Experiments 2+3 analysis
3. Update manuscript
4. Update slides
5. Present

## Current goal

**Experiment 3 runs, then manuscript + slides update for presentation.**

Exp 2 Figure 3 (naive vs optimised metadata comparison) is done and merged (PR #469). §4 prose updated with observed results.

## Workplan

1. **Experiment 3 runs.** Execute intervention arms against frozen Arm 1/Arm 2 baselines (`sota_exp2_naive_arm`, `sota_exp2_brerun1`) and publish run artifacts.
2. **Experiments 2+3 analysis.** Rebuild/refresh derived metrics and comparative tables from the consolidated artifacts.
3. **Update manuscript.** Integrate the Exp 2+3 analysis into report narrative, tables, and claims.
4. **Update slides.** Align conference slides with the refreshed manuscript evidence.
5. **Present.** Final rehearsal and delivery at Econom'IA 2026.

## Backlog (post-conference)

1. **Scaling-curve diagnosis** — direct_complete F1=0 on 3 capable models; likely parser failure on structured-document output.

## Suspended / deferred

**Paper sequencing**: report stays exploratory. Paper writing opens after slides locked post-conference.

Last updated: 2026-05-24T08:30Z

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

**Experiment 3 N=1 gate — launch now, review, then N=2 and N=3.**

All blocking PRs merged (#468 evidence-pack, #474 conversation persistence, #476 Phase-B token floor).
Detection: flag any run where `tokens_out == max_tokens` for Phase A or final Phase B turn (Mistral returns stop not length at cap).

### Launch commands (run from `/home/haduong/aedist-technical-report/`, N=1 gate)

```bash
# Arm 3 (naive + evidence pack, ~2 min for 4 agents)
uv run python experiments/sota/exp2_naive_arm.py \
  --agents mistral openai anthropic qwen \
  --n 1 \
  --output-dir experiments/outputs/sota_exp3_arm3_batch1 \
  --evidence-pack-manifest experiments/evidence_packs/all18tables.yaml

# Arm 4 (optimized multi-turn + evidence pack, ~40 min for 4 agents)
uv run python experiments/sota/exp2_interactive_smoke.py \
  --agents mistral openai anthropic qwen \
  --output-dir experiments/outputs/sota_exp3_arm4_batch1 \
  --evidence-pack-manifest experiments/evidence_packs/all18tables.yaml \
  --no-confirm
```

After N=1: review truncation flags, then rerun with `--run-number 2` (Arm 4) / `--n 2` (Arm 3) for N=2.
Ticket 0250 tracks the full sweep.

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

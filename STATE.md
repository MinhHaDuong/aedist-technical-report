Last updated: 2026-05-24T21:00Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 delivery runway

Conference talk at Thema/Cergy 2026-05-27. Deliverable: French slides + coherent Exp 2/3 narrative.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Milestone: runs → analysis → manuscript → slides → present.

## Current goal

**Experiment 3 four-arm sweep running.** Arms 1–4 launched; output dirs accumulating in `experiments/outputs/sota_exp3_arm{1-4}_batch1/`. Next: review truncation flags across all arms, then Exp 2+3 analysis. Ticket 0250 tracks the full sweep.

## Status
<!-- generated 2026-05-24T21:00Z -->
**Tickets:** 24 ready · 35 open — `erg ready tickets/` for full list
**Recent commits:**
  f60fe18f chore(tickets): archive exp2 mart bundle (0282-0288) — all closed via PR #513/512
  afb666cb Merge pull request #515 — feat(exp2): extend experiment2.mk to cover all four arms
  e83a21cb Merge pull request #514 — fix(ci): keep required rag_extract record fixture tracked
  85ea1653 Merge pull request #513 — feat(exp2): migrate analysis flow to JSON mart with parity gate

## Workplan

1. **Experiment 3 runs.** Four arms against frozen Arm 1/2 baselines; publish artifacts.
2. **Experiments 2+3 analysis.** Rebuild derived metrics and comparative tables.
3. **Update manuscript.** Integrate Exp 2+3 analysis.
4. **Update slides.** Align conference slides with refreshed evidence.
5. **Present.** Final rehearsal and delivery at Econom'IA 2026.

## Backlog / deferred

- Scaling-curve diagnosis — direct_complete F1=0 on 3 capable models (parser failure suspected).
- Paper writing opens after slides locked post-conference.

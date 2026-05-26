Last updated: 2026-05-26T13:29Z

## North star

Produce research-quality energy infrastructure datasets from open sources, validated by a methods benchmark. **Not which model is best, but which method produces trustworthy statistics with locatable errors.** PyPSA-ASEAN remains the long-term target; the benchmark de-risks v1 pipeline design choices. See MASTERPLAN.md.

## Current milestone: Econom'IA 2026 delivery runway

Conference talk at Thema/Cergy 2026-05-27. Deliverable: French slides + coherent Exp 2/3 narrative.
Title: *Beyond RAG: Stateful-Agentic Architectures for Reliable Economic Statistics*
Abstract: `docs/HaDuong-2026-EconomIA-Abstract.md`. Milestone: runs → analysis → manuscript → slides → present.

## Current goal

Finalize slides and manuscript for conference delivery (2026-05-27). Analysis pipeline complete; figures produced for Exp 1, 2, 3; take-home messages ratified.

## Status
<!-- generated 2026-05-26T13:29Z -->

**Tickets:** 29 ready · 4 blocked — `erg ready tickets/` for full list
**Recent commits:**
  2ea1cc2 tickets: archive closed raid batch 0324-0344 to closed/
  bd15908 data(exp2): absorb qwen arm4 run01 rerun on correct model → 80/80 scored
  592d0fa fix(exp2): recover 5 unscored runs (non-canonical headers + earlier-turn)
  3b83100 tickets: open 0345 — collapse Exp2 build to a single producer
  5e7bc0b fix(exp2): recover mistral arm4 run01; guard old qwen

## Workplan

1. **Experiment 3 runs.** DONE.
2. **Experiments analysis.** DONE — Exp 1/2/3 figures produced, take-home messages A–D ratified.
3. **Update manuscript.** Integrate figures and narrative. DONE — 0313–0318 closed.
4. **Update slides.** DONE — review batch 0324–0343 raided + merged (text, figures, restructuration, prompt slides, final order 0341). Exp2 rescored to **80/80** (full 2×2, all correct models: mistral/arm3/4-arm extraction fixes + qwen rerun on qwen3.7-max); coverage figures regenerated + verified. Author hand-tuning slides.tex.
5. **Present.** Final rehearsal and delivery at Econom'IA 2026 (2026-05-27).

## Backlog / deferred

- Scaling-curve diagnosis — direct_complete F1=0 on 3 capable models (parser failure suspected).
- Paper writing opens after slides locked post-conference.
- Makefile DAG: slides build collapsed to single producer + clean-room (0345 done, PR #609); report-side clean-room + uv-run guard deferred (tickets 0352/0353). End-session: prune stale remote branch `origin/t0345-collapse-exp2-single-producer` (orphan, no PR, behind main).
- CI required-checks rule was disabled 2026-05-26 for the conference push — re-enable after the talk.

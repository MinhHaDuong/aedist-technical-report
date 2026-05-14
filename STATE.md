Last updated: 2026-05-10T09:00Z

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

## Priorities (set 2026-04-30, confirmed 2026-05-01)
1. Align workplan on docs/synopsis.md. Do we really need to register, this is not medical trials? 
2. Implement the experiment described in synopsys.md, asking the SOTA for the complete report with per-asset discussion and summary table. **Falsify H0: Deep research agents are enough**.
3. Implement the prototype described in synopsys.md.

## Backlog
1. **Diagnose `direct_complete` F1 = 0.000 rows.** Three capable models (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20) score zero — almost certainly a parser failure on structured-document output. Read one raw `.record.json` + confirm before any priority-3 build. If parser is broken, F1 = 1 is unreachable by construction.
2. **Verify qwen3.5:9b/direct ×3 on coal-only.** Single-run F1 = 0.984 on direct is remarkable; confirm with repeats before deciding whether priority-3 reduces to "use this 9B" vs "build deep-research stack".
3. **Registry / figures infrastructure (new, 0156→0160).** Blocked only by implementation order: 0156 first, then 0157/0159/0160 in parallel.

## Suspended / deferred

**Rerun ablation with verbatim modules.** Ticket 0142 closed (PR #313). Ticket 0143 (rerun) now unblocked. Exit gate: `diff` assembled-composite vs `prompt_complete.txt` = 0 (verified).

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.




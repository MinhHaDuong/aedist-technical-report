Last updated: 2026-05-15T17:00Z

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

## Workplan (set 2026-05-15)

1. **Experiment 1 baseline re-sweep (ticket chain 0174–0178).** Branch `t0174-exp1-baseline` pushed, pending review. Unblocked now: **0175** (lock design — update harness.py _MODULE_ORDER, modules/README.md, experiments.toml, Annex A) and **0176** (reference provenance — write PROVENANCE.md + manuscript paragraph). Blocked: 0177 (45-run sweep) on 0175; 0178 (update manuscript) on 0177.
2. **Implement the SOTA experiment (slides §4 — Falsify H0: Deep research agents are enough).** Umbrella **0166**, four SOTA agents (Anthropic Opus 4.7 / OpenAI GPT-5.5 / Mistral Large 2512 / Qwen3-Max via DashScope). Phase-5 raid in progress; **work moves to padme** for Wave 2 onwards.
   - **Wave 1 (done, merged PR #331):** ticket 0172 — RunRecord schema extension. Pydantic `RunRecord` + `ResourceUse` gained 14 optional agent-mode fields; `records_to_metrics()` projects them per ADR-7.
   - **Wave 2 (ready, padme):** tickets **0167 / 0168 / 0169 / 0173** — four direct-API adapters, parallel. All four blocked-by are now satisfied (0172 merged). Live smokes authorised at $0.50/adapter; 0169 Mistral has a $0.50 pricing-probe pre-gate before its smoke (connector pricing unpublished). 0173 Qwen needs the user to provision a DashScope API key at `~/.config/keys/dashscope.env` before its smoke.
   - **Wave 3 (after Wave 2):** tickets **0170 / 0171** — Phase A reflexive prompt-design harness + Phase C cross-eval (mechanical Accuracy via existing `evaluate.py` / `metrics.py` / `reconcile.py`; 0–3 anchored rubric; parser-enforced quoted-span check).
   - **Phase B (queries):** runs after Wave 3 lands, on explicit user authorisation. Budget cap ~$140 total.
   - Full implementation specs: `tickets/0166-raid-plans.md`. Each adapter ticket has its log-entry with Imagine refinements applied.
3. Implement the prototype described in synopsis (the stateful-agentic v1, synopsis §5). Not yet ticketed; opens after Wave 3 lands and Phase B has run.

## Backlog
1. **Diagnose `direct_complete` F1 = 0.000 rows.** Three capable models (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20) score zero — almost certainly a parser failure on structured-document output. Read one raw `.record.json` + confirm before any priority-3 build. If parser is broken, F1 = 1 is unreachable by construction.
2. **Verify qwen3.5:9b/direct ×3 on coal-only.** Single-run F1 = 0.984 on direct is remarkable; confirm with repeats before deciding whether priority-3 reduces to "use this 9B" vs "build deep-research stack".
3. **Registry / figures infrastructure (new, 0156→0160).** Blocked only by implementation order: 0156 first, then 0157/0159/0160 in parallel.

## Suspended / deferred

**Rerun ablation with verbatim modules.** Ticket 0142 closed (PR #313). Ticket 0143 (rerun) now unblocked. Exit gate: `diff` assembled-composite vs `prompt_complete.txt` = 0 (verified).

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.




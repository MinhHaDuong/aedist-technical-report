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

1. **Falsify H0: Deep research agents are enough**. Ask the SOTA for the complete report with per-asset discussion and summary table, see F1 drop.
2. **Diagnose `direct_complete` F1 = 0.000 rows.** Three capable models (Ernie 4.5 Thinking, GPT-5.4, Grok 4.20) score zero — almost certainly a parser failure on structured-document output. Read one raw `.record.json` + confirm before any priority-3 build. If parser is broken, F1 = 1 is unreachable by construction.
3. **Verify qwen3.5:9b/direct ×3 on coal-only.** Single-run F1 = 0.984 on direct is remarkable; confirm with repeats before deciding whether priority-3 reduces to "use this 9B" vs "build deep-research stack".
4. **Registry / figures infrastructure (new, 0156→0160).** Blocked only by implementation order: 0156 first, then 0157/0159/0160 in parallel.
5. **Rerun ablation with verbatim modules.** Ticket 0142 closed (PR #313). Ticket 0143 (rerun) now unblocked. Exit gate: `diff` assembled-composite vs `prompt_complete.txt` = 0 (verified).

**Paper sequencing**: report stays exploratory. Paper writing opens after slides are locked post-conference.

## Status

Pipeline end-to-end. Benchmark: 57 models, headline F1 macro-wired (`\HeadlineMeanFOne`, deepseek-v3.2/rag_per_fuel, n=4 runs). CI: 1150 passing, 1 skipped, 2 xfailed. `make lint` includes ruff + ticket structure check.

**Argument arc (2026-05-06, finalized):** `docs/synopsis.md` locked. Four quality properties: Accuracy, Coherence, Provenance, Temporality. Four method-ladder limits: Articulation, Coverage, Freshness, Coherence (Provenance unaddressed by any rung). H1–H4 confirmatory hypotheses formulated and registered in `docs/hypotheses.md` and `docs/preregistration-osf.md`.

**H1–H4 (2026-05-06):**
- **H1** (Articulation rung): multi-turn adds measurable F1 over direct; paired ΔF1 ≥ 0.03, p < 0.05
- **H2** (Coverage rung): RAG adds measurable F1 over multi-turn; same decision rule
- **H3** (accuracy–provenance trade-off): single parametric prompt does not simultaneously achieve full recall and verifiable per-row attribution; ΔF1(complete−extract) < −0.10 AND citation validity < 0.50
- **H4** (local approaches frontier): qwen3.5:122b on A4000 GPU within 0.05 F1 of cloud frontier ceiling (0.988)

**Phase 0 gates (2026-05-06):** 0163 ✓ (evaluator correct), 0164 ✓ (price audit), 0150 pending human (~20 min).

**Prompt fixes (2026-05-06):** `prompt_complete.txt` + module files updated: lifecycle scope broadened (proposed→dismantled), count hint removed, LOW-confidence tiebreaker added.

## Blockers

- **0150** OSF preregistration — human action, ~20 min, form at `docs/preregistration-osf.md`. **Must precede all confirmatory sweep runs.**
- **0139** (seed + finish_reason in RunRecord) needed before Phase 3 full runs. Workaround for Phase 1: grep finish_reason from raw JSON manually.

## Priorities (2026-05-06)

1. **0150 OSF preregistration** — human action, unblocks all confirmatory runs.
2. **Phase 1 pilots** (~$2–5): 5 matched frontier models × `prompt_extract` × 3 conditions × 3 reps. Verify finish_reason, row count, F1.
3. **Phase 2 H3 sweep** (~$5–10): 5 models × `prompt_complete_no_web` × 3 reps (Condition A shared with Phase 1 direct).
4. **0165 prompt module–aspect mapping** — design ablation with modules targeting property aspects.
5. **0139 JobSpec** — add seed, provider_order, finish_reason to RunRecord.



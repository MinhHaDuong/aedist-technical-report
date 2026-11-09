# Project memory — aedist-technical-report

v8 repository memory (ticket 0687). This repository is public: write
nothing here that is unfit for a public reader. Canonical state:
[STATE.md](../STATE.md); plan: [MASTERPLAN.md](../MASTERPLAN.md);
decisions: [ADR.md](../ADR.md); work: [tickets/](../tickets/). Documents
govern over topics. Project rules: [.claude/rules/](../.claude/rules/).

Sources and their dispositions: [SOURCES.md](SOURCES.md). The Claude Code
native auto-memory of this project stays active and separate.

## Departments

- [Commission](topics/commission.md) — author rulings: preprint is `main.tex`, "article" = peer-reviewed, concept DOI, merge-review-merge, Imagine dialogue.
- [Experiments](topics/experiments.md) — Exp 1–3 and the case study: design locks, canonical outputs, local-vs-cloud pairing.
- [Measurement](topics/measurement.md) — three-quality frame, coherence composites, `f1=None`, refusals, statistical power.
- [Reference dataset](topics/reference-dataset.md) — never hardcode the count (177, v2.4); no invented names; verbatim data edits.
- [Pipeline and code](topics/pipeline-and-code.md) — P1–P4 build phases, archive outputs, Pydantic and pathlib pitfalls.
- [Providers and runs](topics/providers-and-runs.md) — OpenRouter `reasoning_effort`, free-tier limits, local routing, smoke promotion.
- [Figures and manuscript](topics/figures-and-manuscript.md) — verify claims on raw data, worst-case panel, render tables, plain captions.
- [Repository workflow](topics/repo-workflow.md) — merge commits only, erg close effects, parallel sessions and manuscript waves.

## History

The journal in [journal/2026/](journal/2026/) holds episodes, append-only;
search it with `rg`. Git history holds superseded pages.

# Experiment 1 — Baseline single-prompt inventory

1. **Operationalize the scope.** "Power-plant inventory" is not a closed target. Fix the universe explicitly before measuring anything: e.g., *Vietnam, thermal units ≥30 MW, status ∈ {operating, under construction} as of 2024-12-31*. Without a closed reference population, recall is undefined and precision drifts.

2. **The reference dataset is itself a methodological contribution.** State who curates it, from which primary sources (PDP8 annexes, EVN reports, MOIT decisions), version-locked. Quantify its residual uncertainty (cells flagged as disputed). The baseline's credibility is bounded by the gold standard's, and how the gold standard is built belongs in the paper, not in a footnote.

3. **Decompose the F1.** A single score conflates three failure modes that need separate remedies: (i) entity discovery (row-level P/R), (ii) attribute correctness conditional on correct discovery (cell-level, per attribute), (iii) fabrication rate (rows/cells with no real referent). Each maps to a different lever later.

4. **Report run variance, not just means.** "Numbers shift between runs" is your motivating claim — quantify it. For n=10 repeats at temperatures ∈ {0, 0.7}, report per-cell stability (rank correlation across runs, fraction of cells identical across all repeats). More informative than averaged F1.

5. **Operationalize "F1 vs cost".** Cost is multidimensional: API price, tokens, wall-clock, human curation. Pick one primary axis, report the others. Sweep across 3–5 models spanning small-local → frontier-API to draw a Pareto front. This converts the baseline from a strawman into a substantive result.

# Experiment 2 — Frontier deep-research agents

1. **Pre-register.** Freeze model versions and dates, the three agent choices, the evaluation rubric, the conjecture, and the stopping rule, before running. Deposit on OSF or HAL. Your conjecture is stated as the likely outcome; without pre-registration the experiment reads as confirmatory rather than diagnostic.

2. **Disentangle model effect from prompt effect.** Self-generated prompts vary across agents, confounding model capability with prompt quality. Add a fixed-prompt control arm where all three receive an identical externally-written specification. The contrast *best self-prompt vs fixed prompt* is itself a finding about agent reflexivity.

3. **LLM-as-judge is biased.** Verbosity bias, self-preference, position bias are well-documented. Mitigations: pairwise comparison rather than absolute scoring; rotate which model judges; blind the judge to source-agent identity; human adjudication on a stratified 15–20% sample with reported κ. Without this the ranking is contestable.

4. **Address web non-stationarity.** Deep-research agents browse a moving web; three runs a week apart diverge for non-model reasons. Log every retrieved URL with timestamp, archive via Wayback for reproducibility, and report *source overlap across runs* as a separate stability metric — distinct from output overlap.

5. **Operationalize the four quality dimensions before running.** Accuracy/coherence/provenance/temporality need scoring rubrics with worked examples, otherwise judge agreement collapses and "falls short" becomes unfalsifiable. Concrete anchor: *provenance = share of cells with a URL that, on click-through, actually supports the value claimed* (not merely topically related). Similar anchors for the other three.

# Experiment 3 — Stateful agentic system

1. **Falsifiable success criterion.** "Feasibility" is not a testable claim. Pre-commit: on the same scope as Exp 1–2, the stateful system must improve provenance verifiability by ≥X pp, reduce cross-run variance by ≥Y%, at marginal cost ≤Z€/row. Without numerical targets this section is a demo, not a result.

2. **Be explicit about what is auto-verified.** Internal coherence (totals, units, non-contradiction) and provenance link-resolution are automatable. External accuracy is not, absent ground truth. The risk: a system that scores well on auto-checks while inheriting the deep-research seed's systematic bias. State which dimensions are machine-checked, which are spot-checked by humans, and the sampling rate.

3. **Specify the HITL protocol.** "Memory of human judgments" is doing the heaviest lifting and is least defined. Required: elicitation mode (corrections / ratings / free text), trigger points (per cell, per conflict, per update cycle), annotation budget per asset, retrieval mechanism (how the agent queries memory), and human-hours per 100 rows reported alongside API cost. Otherwise performance is bounded by undisclosed human effort.

4. **Update and conflict-resolution is the contribution.** The stateful claim stands or falls on how new documents revise existing narratives. Spell out: event-sourced append-only log? Source-authority hierarchy (primary > regulator > secondary > press)? Temporal versioning of derived tables? Tie-breaking rule under contradiction? Currently a paragraph; should be a figure with worked examples on a contested asset (e.g., a repowered/renamed plant).

5. **Scope discipline on the promissory notes.** Per-cell provenance, knowledge-graph fusion, and local-model independence are simultaneously deferred to future work *and* used to motivate the present contribution. Either run a minimum-viable ablation now (per-cell provenance on a 20-row pilot; one local model on the seeding step) and report it, or excise the promises. As written they extend the claims beyond the evidence.

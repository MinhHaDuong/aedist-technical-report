# Experiment 1 — Point-by-point reply to reviewer asks

*Internal tracking document. Maps each reviewer ask to the manuscript deliverable that addresses it.*

*Historical note: written before Figure 2 was generated. References to "Figure 2 (Pareto frontier placeholder)" date from the planning era — the figure now exists as the cost × quality scatter (`fig_direct_cost_quality.pdf`) and the caption explicitly notes that no Pareto-efficient envelope is drawn. The replies below are preserved as the reviewer-correspondence record.*

---

## ChatGPT's 5 asks

### 1. Fix the reference task tightly
> *"Choose one country/sector/time slice… Without a bounded task, low F1 can always be dismissed as prompt ambiguity."*

**Reply:** Addressed in the Experiment 1 scientific paragraph and Annex A. The reference population is `vietnam_thermal_v1.csv`: 163 thermal power plants (coal and gas/gas-oil), all lifecycle statuses, Vietnam only. The reference is version-locked. The Annex A task description makes this explicit.

### 2. Separate row discovery from cell extraction
> *"Score entity-level discovery separately from attributes: name, capacity, fuel, status, location, commissioning year, operator, source."*

**Reply:** Addressed in Annex A (evaluation section). The evaluator scores row-level tp/fp/fn/F1 separately from cell-level fuel accuracy, status accuracy, and province accuracy for matched rows. This decomposition is already live in `measurements.jsonl` for the pilot runs.

### 3. Use repeated runs with controlled randomness
> *"Run the same prompt at least 5–10 times per model/settings combination, not just once. Record variance."*

**Reply:** Addressed in Annex A (run parameters). Design: 5 repeats per model, T=0. Expected-results paragraph explicitly reports within-model F1 variance from pilot data. Figure 1 shows each run as a separate point. Ticket 0177 implements this.

### 4. Define hallucination classes
> *"Code errors as: nonexistent plant, duplicate plant, wrong capacity, wrong status, wrong date, unsupported citation, fake citation, stale value."*

**Reply:** Partially addressed. The evaluator already distinguishes over-listing (high fp, zero fn — model lists everything) from under-listing (zero fp, high fn — model lists only confident plants). These two patterns appear explicitly in the Figure 1 caption and the expected-results paragraph. A full per-class taxonomy would require post-hoc coding of fp rows; this is deferred, as the tp/fp/fn split already distinguishes the two dominant failure modes without new coding.

### 5. Include a cost/time/quality curve
> *"Report cost, latency, number of tokens, and F1/provenance score."*

**Reply:** Addressed in Annex A (evaluation section: cost_usd, wall_s, tokens_out per run) and Figure 2 (Pareto frontier placeholder). The expected-results paragraph notes the absence of a monotonic cost/quality relationship as a substantive finding. Figure 2 is the deliverable.

---

## Claude's 5 asks

### 1. Operationalize the scope
> *"Fix the universe explicitly before measuring anything: Vietnam, thermal units ≥30 MW, status ∈ {operating, under construction} as of 2024-12-31. Without a closed reference population, recall is undefined."*

**Reply:** Addressed in Annex A (task section) and the scientific paragraph. Population: 163 plants, all fuels, all statuses. The reference does not apply a capacity cutoff (the 163-plant reference includes all tracked units regardless of size). Status coverage includes all lifecycle stages — this is wider than Claude's suggested scope, which is intentional: a system that handles only operating/constructing plants is not useful for scenario planning.

### 2. The reference dataset is itself a methodological contribution
> *"State who curates it, from which primary sources, version-locked. Quantify residual uncertainty."*

**Reply:** Addressed by ticket 0176 (reference provenance). Annex A names the primary sources. Full provenance description (construction method, conflict resolution, residual uncertainty for the 62 proposed + 21 planned rows) is the deliverable of 0176, added as a manuscript paragraph and `data/reference/PROVENANCE.md`.

### 3. Decompose the F1
> *"Three failure modes: (i) entity discovery, (ii) attribute correctness conditional on correct discovery, (iii) fabrication rate."*

**Reply:** Addressed in Annex A and the expected-results paragraph. The evaluator provides (i) via tp/fp/fn and (ii) via per-attribute accuracy on matched rows. Mode (iii) — fabrication rate, distinguishing invented plants from real-but-out-of-scope plants in the fp set — is the same partial gap noted for ChatGPT ask 4. The over-listing/under-listing distinction in the expected-results paragraph captures the dominant signal without requiring per-fp coding.

### 4. Report run variance, not just means
> *"For n=10 repeats at temperatures ∈ {0, 0.7}, report per-cell stability."*

**Reply:** Addressed. Five repeats at T=0 are planned (Annex A). The expected-results paragraph quantifies pilot within-model F1 range (0.3–0.4 points). Figure 1 shows each run separately. A temperature sweep (T=0 vs T=0.7) is not implemented — with T=0, residual variance measures prompt and provider non-determinism directly, which is the stronger empirical claim.

### 5. Operationalize "F1 vs cost" — sweep small-local → frontier for Pareto front
> *"Pick one primary axis, report the others. Sweep across 3–5 models spanning small-local → frontier-API."*

**Reply:** Addressed in Figure 2 (Pareto frontier placeholder spanning Experiments 1–3). The journal model set spans cheap reasoning models ($0.07/M) through frontier-class ($7.50/M). A local model is not in `modelset_exp1_journal` — this is a scope decision to revisit in ticket 0175 if the local/sovereign comparison is needed for Experiment 1 specifically (vs. being implicit in the census data).

---

## Summary table

| Ask | Reviewer | Deliverable | Status |
|---|---|---|---|
| Fix reference task | ChatGPT 1 | Annex A task section | Done |
| Separate row/cell scoring | ChatGPT 2 | Annex A evaluation; pilot data | Done |
| 5+ repeats, record variance | ChatGPT 3 | Annex A run params; ticket 0177 | Done (pending sweep) |
| Hallucination taxonomy | ChatGPT 4 | over/under-listing in paragraph; Figure 1 | Partial |
| Cost/quality curve | ChatGPT 5 | Figure 2 placeholder; Annex A metrics | Done (pending sweep) |
| Closed scope | Claude 1 | Annex A task section | Done |
| Reference provenance | Claude 2 | Ticket 0176; PROVENANCE.md | Pending |
| Decompose F1 three ways | Claude 3 | Annex A + expected-results paragraph | Partial |
| Run variance quantified | Claude 4 | Expected-results paragraph; Figure 1 | Done (pending sweep) |
| Pareto front | Claude 5 | Figure 2 placeholder | Done (pending sweep) |

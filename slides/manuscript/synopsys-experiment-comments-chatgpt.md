Yes. The three experiments are promising, but right now they risk reading as *illustrative demos* rather than publishable empirical evidence. You need sharper controls, stable evaluation objects, and less dependence on “model judges.” Below are the concrete improvements I would require as supervisor.

The three proposed experiments are: the naïve one-shot LLM baseline, the frontier-agent/deep-research comparison, and the tailored stateful statistical workflow. The synopsis already defines the quality bar as accuracy, coherence, provenance, and temporality, which is the right evaluation frame. 

## 1. Experiment 1 — naïve one-shot LLM baseline

Current role: establish that direct prompting produces an “inventory-shaped answer” but not a scientific dataset. 

| Improvement point                               | What to do                                                                                                                                      | Why it matters                                                                                                                                          |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Fix the reference task tightly               | Choose one country/sector/time slice, for example “coal and gas power plants in Vietnam, operating or planned as of date X.”                    | Without a bounded task, low F1 can always be dismissed as prompt ambiguity.                                                                             |
| 2. Separate row discovery from cell extraction  | Score entity-level discovery separately from attributes: name, capacity, fuel, status, location, commissioning year, operator, source.          | A model may find the right plants but hallucinate attributes, or miss plants but extract good data for the ones it finds. These are different failures. |
| 3. Use repeated runs with controlled randomness | Run the same prompt at least 5–10 times per model/settings combination, not just once. Record variance.                                         | The baseline claim is partly about instability: “numbers shift between runs.” You need to measure that, not merely assert it.                           |
| 4. Define hallucination classes                 | Code errors as: nonexistent plant, duplicate plant, wrong capacity, wrong status, wrong date, unsupported citation, fake citation, stale value. | This converts a generic “LLMs are unreliable” claim into a useful diagnostic taxonomy.                                                                  |
| 5. Include a cost/time/quality curve            | Report cost, latency, number of tokens, and F1/provenance score.                                                                                | The baseline is not only “bad”; it may be cheap. The reader needs to see whether later systems buy quality at reasonable marginal cost.                 |

My supervisory push: **do not let this become a straw man.** Use a competent prompt, not a deliberately weak one. The baseline should be “reasonable analyst asks a normal LLM for the table,” not “we made the model fail.”

## 2. Experiment 2 — commercial frontier agents / deep research

Current role: test whether state-of-the-art web-enabled reasoning agents improve over the baseline but still fall short of research-grade statistical quality. 

| Improvement point                                    | What to do                                                                                                                                                                  | Why it matters                                                                                                     |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 1. Standardize the task prompt after self-prompting  | Let models propose optimized prompts, but then freeze a common task specification and quality rubric for all runs.                                                          | Otherwise differences reflect prompt-design variation rather than system capability.                               |
| 2. Avoid circular model-judge evaluation             | Use human-coded gold data for core metrics. Model judges can assist, but not be the final authority.                                                                        | Having “other two models” judge outputs is useful for triage, but weak as evidence. It invites reviewer criticism. |
| 3. Blind the evaluation                              | Strip model/provider identity from outputs before human or model-assisted assessment.                                                                                       | Prevents brand expectations from influencing judgments.                                                            |
| 4. Add source-support auditing                       | Sample claimed citations and verify whether each citation actually supports the claimed row/cell. Score support as exact, partial, irrelevant, inaccessible, or fabricated. | Provenance is one of your core quality dimensions. A source list is not provenance.                                |
| 5. Compare against a non-LLM or semi-manual baseline | Include a conventional web-search/manual spreadsheet baseline, even on a small sample.                                                                                      | The relevant question is not “better than one-shot LLM?” but “better than current analyst practice per euro/hour?” |

My supervisory push: **the “three agents × three runs” design is too small if you want quantitative claims.** It is acceptable for an exploratory paper, but then you must say so. For stronger claims, increase repetitions or narrow the domain so manual evaluation is feasible.

Also: be careful with “different providers.” If you change both model and provider, you confound model capability, tool access, search backend, browsing policy, and context length. Better design:

| Factor                    | Better controlled design                   |
| ------------------------- | ------------------------------------------ |
| Model                     | Same model family where possible           |
| Provider/tool environment | Keep constant where possible               |
| Prompt                    | Fixed after preliminary calibration        |
| Budget                    | Fixed wall-clock, token, and dollar budget |
| Output schema             | Fixed required table and source format     |

## 3. Experiment 3 — tailored stateful workflow

Current role: demonstrate that a scripted, stateful architecture can achieve acceptable row-level scientific quality by maintaining sourced asset histories, with the statistical table as a derived artifact. 

| Improvement point                         | What to do                                                                                                                                                 | Why it matters                                                                                                |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 1. Define the knowledge object precisely  | Specify whether the stateful store contains narratives, claims, evidence snippets, source documents, confidence scores, or all of these.                   | “Narrative asset histories” is appealing, but reviewers will ask what the machine-readable state actually is. |
| 2. Make the update experiment central     | Test not only initial dataset construction, but incremental updates: new document arrives → system updates affected assets → preserves old values/history. | Temporality is one of your strongest conceptual claims. The experiment should showcase it directly.           |
| 3. Test conflict handling explicitly      | Include cases where sources disagree on capacity, status, name, date, or ownership. Require the system to preserve alternatives and justify resolution.    | This is where a stateful scientific system is clearly superior to a one-shot table generator.                 |
| 4. Measure human correction efficiency    | Track how many human interventions are needed, what type, and whether later similar cases improve through stored judgments.                                | The “memory of human judgements” claim needs evidence. Otherwise it sounds like architecture prose.           |
| 5. Evaluate derived-table reproducibility | Given the same knowledge base and extraction rules, regenerate the statistical table repeatedly and verify identical outputs.                              | This distinguishes a scientific data pipeline from a stochastic report-writing agent.                         |

My supervisory push: **this is the main contribution, so do not underspecify it.** The paper should not merely say “a tailored solution can work”; it should demonstrate *which part* works: row discovery, source grounding, update handling, contradiction management, or table derivation.

A strong version of Experiment 3 would include three test bundles:

| Bundle       | Purpose                                                                       |
| ------------ | ----------------------------------------------------------------------------- |
| Clean cases  | Plants with clear primary sources and stable attributes                       |
| Messy cases  | Renamings, phased capacity, contradictory sources, cancelled/planned projects |
| Update cases | New document changes status, date, ownership, or capacity                     |

## Cross-cutting concerns across all three experiments

You need a common scoring sheet. I would use this:

| Dimension       | Metric                                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| Row accuracy    | Precision, recall, F1 against curated reference inventory                                                |
| Cell accuracy   | Attribute-level exact/acceptable/wrong/missing                                                           |
| Provenance      | % rows/cells with source; % sources that genuinely support claim                                         |
| Coherence       | Number of violated constraints: duplicates, impossible dates, capacity mismatches, status contradictions |
| Temporality     | % claims with as-of date or validity period; ability to distinguish report date from fact date           |
| Reproducibility | Output variance across repeated runs                                                                     |
| Cost            | Dollar cost, runtime, human review time                                                                  |

The most important design correction: **keep the evaluation object constant across all three experiments.** Same country, same technology scope, same time boundary, same gold standard, same scoring rubric. Otherwise the paper becomes a sequence of anecdotes.

## Ranked recommendation

1. **Make Experiment 3 the centerpiece.** That is where your real novelty lies.
2. **Use Experiment 1 as a disciplined failure baseline**, not a rhetorical punching bag.
3. **Use Experiment 2 as a frontier comparison**, but avoid overclaiming because commercial agents are moving targets.
4. **Replace model-judge evaluation with human-audited metrics**, using LLMs only as assistants.
5. **Add temporality and update handling as explicit tests**, because that is where your architecture most clearly beats ordinary RAG.

My blunt assessment: the paper has a good architecture argument, but the experiments need to become more adversarial. Right now they mostly ask, “Can the system produce a better table?” The stronger question is: **Can the system maintain a defensible statistical object under missing evidence, conflicting sources, and time-varying facts?** That is the publishable version.


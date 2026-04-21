# Prompt-optimizer survey: framework selection for the universal prompt

*Decision memo — supports ticket 0075. Engineer-facing, not a lit review.*
*See `docs/quality-grounding.md` for what "quality" means and which metrics we optimize.*

---

## 1. Context and objective

The AEDIST pipeline extracts structured energy-infrastructure tables from
government planning documents (seed extraction). The goal is a prompt
*template* parameterized by `(asset_class, country)` that works across a
60-cell matrix (~10 ASEAN countries × ~6 asset classes) without per-cell
re-tuning. That is the sense of "universal."

**Optimization objective** (per ticket 0075):

> `max min_{m in M5} [ recall(m) × hallucination_gate(m) ]`
> subject to cost ≤ $0.06 / campaign

where `M5` is a fixed set of five cheap models spanning at least three
providers (OpenRouter, Ollama, direct API), `hallucination_gate(m) = 1`
iff zero fabricated entries, and `recall` is fraction of reference assets
found. The objective minimizes over models — the prompt must lift the
*floor*, not ride one strong model.

**What the optimizer does not control.** Evidence scores (the 0–5
source-quality ladder in `quality-grounding.md`) are the verification
pipeline's job. The prompt produces the seed table; the optimizer may
treat evidence as an observed outcome but must not optimize it.

**Prior.** DSPy, unless a structural incompatibility rules it out.

**Non-goal.** This memo does not select the five cheap models, run a
prototype, or report before/after numbers. Those are Phase 1 actions
in ticket 0075. The prototype is deferred to a follow-up ticket once
this survey is ratified.

---

## 2. Framework cards

### 2.1 DSPy (Stanford, 2023–present)

**What it does.** DSPy separates the *program structure* (typed
`Signature` and `Module` objects) from the *prompt text*, which the
framework generates and optimizes. Optimizers — `BootstrapFewShot`,
`MIPROv2`, `COPRO`, `BootstrapFinetune` — search over instruction
text and few-shot demonstrations using Bayesian optimization or
bootstrap sampling. MIPROv2 (Khattab et al., arXiv 2406.11695) is the
current flagship: it proposes instructions via an LLM, then runs
discrete search over (instruction, demos) pairs against a validation
metric.

**Metric interface.** A DSPy metric is an arbitrary Python callable
`metric(example, prediction, trace=None) -> float | bool`. The
`Evaluate` harness invokes this callable concurrently (`num_threads`
parameter) over a dev set. Nothing in the framework couples the metric
to a specific LM; the callable can internally loop over multiple models
and return the minimum. The constraint from ticket 0075 —
`min_of_5(recall × hallucination_gate)` — maps directly onto this
interface. A thin wrapper that calls each of the five models, collects
the recall and hallucination_gate, and returns the minimum is all that
is needed; no DSPy internals need to change.

**Multi-provider support.** DSPy uses LiteLLM as its adapter layer.
LiteLLM covers OpenAI, Anthropic, and any OpenAI-compatible endpoint
(including OpenRouter). Ollama is supported via `ollama/model-name`
routing through LiteLLM. All four providers required by this project
are covered without custom adapters.

**Dependency weight.** `dspy-ai` pulls in LiteLLM, `pydantic`, and
`optuna` (for MIPROv2 Bayesian search). No LangChain. The footprint is
moderate; the package is pip-installable and does not require a running
service. Compatible with the project's flat `pyproject.toml` + Make
pipeline.

**Reproducibility.** MIPROv2 accepts `seed` and `log_dir` parameters.
Optimizer traces (intermediate prompts, trial scores) are written to a
separate directory, not to `measurements.jsonl`. This respects the
measurement-hygiene wall: engineering artifacts stay in a
`experiments/optimizer_runs/` subtree; only the final held-out
evaluation writes to `measurements.jsonl`.

**Known limitations.**
- Optimization cost scales with `num_trials × devset_size × num_models`.
  For our 5-model objective, each trial evaluates the candidate prompt
  against all five models. Budget must be set explicitly via
  `max_bootstrapped_demos` and `num_trials`.
- MIPROv2 assumes the teacher LM (the one proposing instructions) is
  capable of meta-reasoning. Using a very cheap model as teacher
  degrades proposal quality; a modest frontier model (e.g., a mid-tier
  OpenRouter model) is needed as the optimizer LM while cheap models
  are the *evaluated* LMs.
- The framework was designed for QA and classification tasks; it has no
  special handling for structured table output. The metric and the
  `Signature` schema must encode the extraction format explicitly. This
  is a configuration task, not a structural barrier.

**Verdict.** Strong fit. Adopt for Phase 1 prototype.

---

### 2.2 TextGrad (Stanford/Zou Group, 2024)

**What it does.** TextGrad implements backpropagation through LLM calls
via "textual gradients" — natural-language feedback propagated backward
through a computation graph. Published in *Nature* (Yuksekgonul et al.,
arXiv 2406.07496). Shown to improve coding (LeetCode-Hard +20%),
reasoning (GSM8K 72.9% → 81.1%), and molecular design.

**Metric interface.** TextGrad's backward pass requires that each node
in the graph be differentiable through a *specific* student LM — the
LM that receives the gradient signal must be the same LM whose prompt
is being updated. The framework is architecturally designed for
single-LM optimization: you optimize a prompt for one model, then
optionally transfer it.

**Multi-model fit.** This is a structural mismatch. Our objective is
`min_of_5` over five different models simultaneously. TextGrad would
require running five separate optimization loops (one per model) and
then intersecting the resulting prompts — a heuristic with no guarantee
of convergence. The "textual gradient" metaphor breaks down when the
backward signal must be averaged over heterogeneous models.

**Dependency weight.** Pulls in a heavier dependency graph than DSPy;
requires a specific version of `torch` or an LLM inference backend.

**Known limitations.** High API cost per optimization step (multiple
forward + backward calls). Optimized prompts tend to be long and model-
idiomatic, which conflicts with cross-model portability. No native
multi-provider adapter beyond OpenAI.

**Verdict.** Defer. Compelling for single-model pipeline optimization
(e.g., future work on the verification sub-pipeline). Not suitable for
the min-of-5 objective.

---

### 2.3 OPRO — Large Language Models as Optimizers (Google DeepMind, 2023)

**What it does.** OPRO describes the optimization task in a meta-prompt
containing previous (prompt, score) pairs, then asks an optimizer LLM
to propose new candidate prompts (Yang et al., arXiv 2309.03409,
ICLR 2024). Evaluation is a black-box scorer LLM call. Best results on
GSM8K (+8% over human prompts) and BIG-Bench Hard (+50%).

**Metric interface.** OPRO accepts any scalar score — the meta-prompt
includes `(candidate_prompt, score)` examples. The score can be the
output of an arbitrary evaluation function, including our
`min_of_5(recall × hallucination_gate)`. The optimizer is agnostic to
how the score was produced.

**Multi-model fit.** Black-box score interface naturally accommodates
multi-model evaluation: compute the score externally across five models,
pass the scalar to the meta-prompt. Wrapper complexity is similar to
DSPy.

**Known limitations.**
- The reference implementation (github.com/google-deepmind/opro) is a
  research artifact targeting Google's PaLM-2 family. It is not
  packaged as a maintained library. Community ports exist but vary in
  quality.
- No few-shot demonstration optimization — OPRO only tunes instruction
  text. DSPy's MIPROv2 tunes both instructions and demonstrations,
  giving a larger search space.
- Effectiveness degrades with smaller optimizer LMs (arXiv 2405.10276).
  Requires a frontier-class optimizer LM, increasing cost.
- No built-in reproducibility infrastructure (seed logging, trace
  storage). Would require custom scaffolding to maintain the
  measurement-hygiene wall.

**Verdict.** Defer. The principle is sound and the black-box interface
fits; but the reference implementation requires significant wrapping to
meet our reproducibility and multi-provider requirements. DSPy subsumes
OPRO's core idea (instruction proposal via LLM) within a more mature
engineering harness.

---

### 2.4 Promptbreeder (Google DeepMind, 2023)

**What it does.** Evolutionary population of task-prompts. Fitness is
evaluated by a scorer LM on a training set. Mutation-prompts are
themselves evolved (self-referential). Published as Fernando et al.,
arXiv 2309.16797.

**Metric interface.** Binary fitness (correct/incorrect on training
examples). Can be adapted to continuous scores with effort.

**Fit assessment.** Self-referential mutation is expensive (O(population
size × generations) LM calls). No packaged library; paper + community
implementations only. The evolutionary overhead is hard to justify
given DSPy's more sample-efficient Bayesian search. The self-mutation
idea is interesting but orthogonal to our core need.

**Verdict.** Reject for now. Research artifact, high cost, no
engineering infrastructure. Revisit if MIPROv2 plateau is observed.

---

### 2.5 APE — Automatic Prompt Engineer (Zhou et al., 2022)

**What it does.** Generates N candidate instructions by prompting an
LLM with input-output pairs, scores them, resample top-K variants.
Simple, interpretable, fast.

**Fit assessment.** APE is the conceptual baseline that DSPy's
BootstrapFewShot and COPRO subsume. No maintained library. The
technique requires the instruction-generation LLM to be capable enough
to generalize from a handful of examples — thin for low-resource
settings. Does not handle demonstrations, only instruction text.

**Verdict.** Reject. Superseded by DSPy COPRO/MIPROv2 in every
relevant dimension. Useful as a conceptual reference in the article.

---

### 2.6 AdalFlow / Trace (SylphAI, 2024–2025)

**What it does.** AdalFlow (github.com/SylphAI-Inc/AdalFlow) frames
LLM pipelines as computation graphs and applies automatic
differentiation for joint optimization of instruction, few-shot
examples, and prompt template. Architecturally similar to TextGrad but
with a tighter engineering focus and model-agnostic components
(Generator, Retriever, Embedder all switchable by provider). Research
claims highest accuracy among auto-prompt optimization libraries on
several benchmarks.

**Fit assessment.** The model-agnostic component story is promising for
multi-provider coverage. However, AdalFlow's auto-diff approach shares
TextGrad's structural coupling: gradients propagate through a specific
student LM. The min-of-5 objective would require the same multi-loop
workaround. The library is younger and less battle-tested than DSPy;
community and documentation are thinner. Worth re-evaluating in 12
months if the gradient-based approach matures.

**Verdict.** Defer. Monitor for a multi-LM gradient aggregation
mechanism; if one appears, reconsider before Phase 4.

---

### 2.7 Balukosuri autoresearch skill (2026)

**What it does.** A Claude Code / Cursor skill implementing Karpathy's
autoresearch loop: scan repo → define eval criteria → autonomous
modify → verify → keep/discard → repeat. Balu Kosuri's variant
(github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill)
makes the skill repo-generic. Related forks (e.g., uditgoenka/autoresearch)
add structured iteration with logged traces.

**Fit assessment.** This is a meta-skill for an agentic assistant, not
a prompt-optimization library. It has no structured metric interface,
no dev-set harness, no seed control, and no measurement-hygiene
infrastructure. It can call arbitrary tools — including DSPy — but adds
no optimization logic itself. The "autoresearch" name is suggestive but
the mechanism is an agent loop, not a gradient descent or Bayesian
search.

For our use case: the measurement-hygiene wall (engineering artifacts
must not contaminate `measurements.jsonl`) requires deterministic
replay with seed control. An agentic loop that modifies prompts and
reruns experiments without structured logging cannot satisfy this.

**Verdict.** Reject as a standalone optimizer. Valuable as inspiration
and as a wrapper that could *invoke* DSPy from a Claude Code session.

---

## 3. Comparative fit assessment

| Framework | min-of-N support | Arbitrary metric API | Multi-provider | Extraction (not QA) | Dependency weight | Reproducibility | Verdict |
|-----------|-----------------|---------------------|---------------|---------------------|-------------------|-----------------|---------|
| **DSPy MIPROv2** | Via metric wrapper | Yes — Python callable | LiteLLM: OpenAI, Anthropic, OpenRouter, Ollama | Configurable via Signature schema | Moderate (pip, no service) | Built-in seed + trace logging | **Adopt** |
| TextGrad | No — single-LM by design | No — backward requires student LM | OpenAI-centric | Pipeline-friendly but model-locked | Heavy (torch) | Limited | Defer |
| OPRO | Via scalar score | Yes — black-box | Requires wrapping | Yes | Low (research artifact) | Not built-in | Defer |
| Promptbreeder | Via fitness function | Binary, adaptable | Requires wrapping | Yes | None (no library) | Not built-in | Reject |
| APE | N/A | Via scorer LM | Requires wrapping | Yes | None (no library) | Not built-in | Reject |
| AdalFlow | No — gradient-coupled | Auto-diff only | Model-agnostic components | Pipeline-friendly | Moderate-heavy | Partial | Defer |
| Balukosuri skill | No | None | Agent-invoked | N/A | None (skill only) | No | Reject as optimizer |

The discriminating constraint is the min-of-N-models objective. Any
framework that couples its optimization signal to a single student LM
(TextGrad, AdalFlow's current gradient path) fails structurally.
Black-box metric interfaces (DSPy, OPRO) pass. Among those, DSPy wins
on engineering maturity and provider coverage.

---

## 4. Recommendation

### Adopt: DSPy MIPROv2

**Rationale.** DSPy is the only candidate that combines:
1. A Python-callable metric interface that natively accepts
   `min_of_5(recall × hallucination_gate)` as a black-box score.
2. Multi-provider LM coverage via LiteLLM (all four providers used by
   the project: OpenAI, Anthropic, OpenRouter, Ollama).
3. Joint optimization of instruction text and few-shot demonstrations
   — a larger search space than instruction-only methods.
4. Built-in seed control and trace logging, enabling the measurement-
   hygiene wall between optimizer artifacts and published measurements.
5. Active maintenance and a growing community; the framework is not a
   research artifact.

**Caveat on teacher LM cost.** MIPROv2 uses an optimizer LM to propose
instructions. This LM should be at least a mid-tier frontier model.
The five *evaluated* models are the cheap ones; the *optimizer* LM is
used only during optimization, not inference. This adds a one-time
budget item (roughly: `num_trials × cost_per_optimizer_call`). Must be
planned explicitly in the Phase 1 prototype budget.

**Caveat on schema lock.** Before running MIPROv2, lock the output
CSV schema (`column names`, `fuel` and `status` enum values) and the
reconciliation parameters. The optimizer may change instruction and
demonstration text, but must not drift the ontology (see
`quality-grounding.md §2.4`). Add a schema-validation gate inside the
metric callable.

### Defer: OPRO

OPRO's black-box scalar interface is conceptually sound. Defer until
the Phase 1 DSPy prototype is evaluated; if MIPROv2 plateaus, OPRO
provides a lightweight fallback with lower infrastructure overhead.

### Defer: TextGrad, AdalFlow

Both have genuine strengths for single-model optimization pipelines.
Revisit for the verification sub-pipeline (evidence scoring, cross-
check routing) where single-LM gradient feedback may outperform
Bayesian search.

### Reject: Promptbreeder, APE

Superseded by MIPROv2 in the relevant dimensions. Retain as conceptual
references in the article's methods section.

### Reject: Balukosuri autoresearch skill as optimizer

Can serve as an agentic wrapper that invokes DSPy within a Claude Code
session, but adds no optimization logic itself.

---

## 5. Next step

Open a follow-up ticket for the Phase 1 prototype:
- Wire `min_of_5(recall × hallucination_gate)` as a DSPy metric.
- Select five cheap models from `experiments/experiments.toml` spanning
  OpenRouter, Ollama, and at least one direct API.
- Run MIPROv2 on the Vietnam/thermal dev set under a fixed API budget.
- Score the optimized prompt on the held-out verification sweep
  (ticket 0030) to detect overfitting.
- Report before/after table: recall per model, hallucination count,
  min-of-5 score, cost, wall-clock time.

Optimizer artifacts (traces, intermediate prompts, per-trial scores)
must be stored outside `experiments/outputs/` — suggest
`experiments/optimizer_runs/` with a `.gitignore` entry for large
trace files. Only the final held-out evaluation writes to
`measurements.jsonl` through the standard harness.

---

## References

- Khattab, O. et al. (2023). *DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines*. arXiv 2310.03714.
- Singhania, S. et al. (2024). *Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs* (MIPROv2). arXiv 2406.11695.
- Yuksekgonul, M. et al. (2024). *TextGrad: Automatic "Differentiation" via Text*. arXiv 2406.07496. Published in *Nature*.
- Yang, C. et al. (2024). *Large Language Models as Optimizers* (OPRO). arXiv 2309.03409. ICLR 2024.
- Fernando, C. et al. (2023). *Promptbreeder: Self-Referential Self-Improvement via Prompt Evolution*. arXiv 2309.16797.
- Zhou, Y. et al. (2022). *Large Language Models Are Human-Level Prompt Engineers* (APE). arXiv 2211.01910.
- Yin, L. et al. (2024). *AdalFlow: The Library to Build and Auto-Optimize LLM Applications*. github.com/SylphAI-Inc/AdalFlow.
- Liu, P. et al. (2025). *Revisiting OPRO: The Limitations of Small-Scale LLMs as Optimizers*. arXiv 2405.10276.

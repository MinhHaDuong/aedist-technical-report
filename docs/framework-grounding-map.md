# Framework-grounding concept map

*Mapping between `measurement-framework.md` (four limits, three
qualities) and `quality-grounding.md` (philosophy of science,
professional codes, operational metrics). After ticket 0147, this
content folds into `argument.md`.*

## Concept mapping table

| Framework concept | Quality | Grounding analogue | Match | Disambiguation |
|---|---|---|---|---|
| **Articulation** (limit) | answer | Theory-ladenness, prompt-as-lens (QG §2.4) | approximate | Framework emphasises prompt *clarity* across the human-model barrier. Grounding emphasises ontological *stability* under optimisation (same concern, different emphasis). No metric directly operationalises Articulation; the ablation study is the closest measurement (prompt structure drives F1). |
| **Coverage** (limit) | data | Coverage (recall) metric, `metrics.py:61`; empirical adequacy (QG §2.1) | operationalises | The recall metric *measures* the limit: `coverage = n_matched / n_reference` quantifies whether training-absent facts were recovered. Same word, same concept, different abstraction level. See §Coverage disambiguation below. |
| **Freshness** (limit) | data | DQAF Timeliness (QG §3.2) | approximate | Framework: input-data staleness (facts moved on since training cutoff). DQAF Timeliness: report publication latency (wall-clock time). Same temporal dimension, different referent. The project records wall-clock time but does not yet measure input-data currency against a dated reference. |
| **Coherence** (limit) | answer | Coherence data model (QG §4); DQAF coherence (QG §3.2) | approximate | Framework: weak/internal self-consistency of extracted claims (Wang et al. 2022). Grounding: row-level / cross-row / aggregate table consistency via `coherence.py`. Both target internal consistency, but the mechanisms differ: framework reasons about claim-level sampling agreement, grounding checks structural table rules. See §Coherence disambiguation below. |
| **Method quality — verifiable** (axis) | method | Evidence score 1-3; Falsifiability (QG §2.2) | operationalises | A citation makes a claim falsifiable (Popper). Evidence score 1-3 classifies whether a source is offered, secondary, or primary. One agent with the right prompt can reach this floor. |
| **Method quality — verified** (axis) | method | Evidence score 4-5; Corroboration (QG §2.2) | operationalises | Confirmed/corroborated sources. Evidence score 4 = one primary source confirmed (HITL); score 5 = two independent primaries confirmed. Requires a second system or human re-reading the source — the natural role for multi-agent verification (framework §Method quality). |

## Orphan concepts

Grounding concepts without a framework limit:

- **Precision** (`n_matched / n_system`). Captured by F1 but no named limit corresponds to it. Precision measures over-generation (hallucinated plants), which is an *answer-quality* failure orthogonal to the four limits. The framework implicitly treats it as a component of Articulation (the model answered a question it was not asked), but this is not explicit.
- **Attribute accuracy** (fuel, status, province, capacity). Fine-grained correctness within matched records. Subsumed by Articulation loosely (did the model state facts correctly?) but at a granularity below the framework's unit of analysis.
- **Reproducibility** (QG §2.3). Intersubjective agreement across models and runs. The framework treats this as a *property of the experimental design* (multiple models x multiple runs), not as a fifth limit. No orphan: it is the method by which all four limits are measured, not a separate concept to close.
- **UN/IMF/ASA/ISI professional codes** (QG §§3.1-3.4). Institutional and ethical framing. The framework's three-quality structure is a conceptual decomposition of what these codes demand; the codes ground the decomposition, not the other way around.

Framework concepts without a grounding analogue:

- None. Every framework concept is touched by at least one grounding section. The grounding document is broader in scope (it covers institutional context the framework does not need), but nothing in the framework is left ungrounded.

## Coverage disambiguation

The word "Coverage" appears in both documents with the same underlying
meaning at different abstraction levels:

- **Framework (limit):** Coverage is a *data-quality limit* — facts the
  model never saw in training. It is closed by providing documents (RAG)
  or web access.
- **Grounding (metric):** `coverage = n_matched / n_reference` is the
  *recall* of the reconciliation — the fraction of reference plants the
  system found. It operationalises the limit.

The collision is apparent, not real: the metric measures the limit. The
code and output tables already parenthesise the metric as "Coverage
(recall)" in `quality-grounding.md` and "Couverture (recall, coverage)"
in `glossaire.tex`. No rename is needed. The resolution is
disambiguation prose on first use:

- In `measurement-framework.md`, when introducing the Coverage limit:
  add a parenthetical noting that the operational metric is recall
  (`n_matched / n_reference`).
- In `quality-grounding.md`, the existing parenthetical "Coverage
  (recall)" suffices. No change needed.

## Coherence disambiguation

"Coherence" also appears in both documents with overlapping but
distinct meanings:

- **Framework (limit):** Weak/internal self-consistency of extracted
  claims. A model that extracts contradictory facts from the same source
  fails Coherence. The framework cites Wang et al. (2022)
  self-consistency decoding as a mechanism, and explicitly scopes to the
  weak/internal cell of the 2x2 (weak vs. strong, internal vs. external).
- **Grounding (DQAF dimension + data model):** Table-level structural
  consistency. Row-level schema validation, cross-row deduplication,
  aggregate control-total checks. Implemented in `coherence.py`, reported
  per model in `tab_coherence.tex`.

The overlap is substantial: both target "is the output internally
consistent?" But the framework's Coherence is about semantic
self-consistency of claims (would sampling the model again produce a
contradictory answer?), while the grounding's coherence is about
structural table rules (does capacity sum to the control total?). A
table can pass all structural coherence checks while containing
semantically contradictory claims, and vice versa.

Resolution: both meanings are valid and complementary. On first use in
each document, qualify which sense is intended:

- Framework: "Coherence (weak, internal — claim-level self-consistency)"
  is already present in `measurement-framework.md`.
- Grounding: "Coherence (DQAF — table-level structural consistency)" on
  first use in §4 of `quality-grounding.md`.

## Freshness vs. DQAF Timeliness

These are *not* synonyms despite both involving time:

- **Framework Freshness:** the input data is stale relative to ground
  truth. Closed by web access (the model retrieves current information).
- **DQAF Timeliness:** the report is delivered late relative to the
  reference period. Measured by wall-clock time in the pipeline.

The project measures wall-clock time (Timeliness) but does not yet
measure input-data currency against a dated reference (Freshness). This
gap is noted in `measurement-framework.md`'s empirical caveat: the
deep-research cell that should close Freshness has not yet reached its
expected ceiling.

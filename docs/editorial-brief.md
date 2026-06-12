# Editorial brief — standing editorial decisions

Standing editorial decisions for `slides/manuscript/main.tex`. CI enforces
only mechanical checks and *negative* guards (forbidden phrasings); the
positive intent behind each decision lives here and is checked at review
time by the `/review-pr-prose` panel against every manuscript diff (CI test
polarity rule, `.claude/rules/writing.md`, ticket 0557).

Entry format: one H2 per decision, slug-style heading, with
**Decision:** / **Rationale:** / **Originating ticket:** / **Status:**.
A decision is retired by flipping **Status:** to `retired (reason)`,
never by deleting the entry.

## lifecycle-scope

**Decision:** The abstract disambiguates the 177-plant register as spanning
the whole project lifecycle (proposed, planned, operating, cancelled,
retired) — it must never read as an operating-only register.

**Rationale:** "177 plants" without the lifecycle scope invites comparison
with operating-fleet counts (~50–60 plants) and makes the benchmark look
inflated. CI keeps the negative guard ("operating plants" /
"operating-only" forbidden in the abstract); the positive wording is free.

**Originating ticket:** 0532 (round 2, author reading-1 brief); demoted from
CI by 0557.

**Status:** active

## rho-caveat-conclusion

**Decision:** If the conclusion cites the ρ = 0.92 screen correlation, the
sentence carries the pooled-across-models and in-sample qualifications and
points to the within-model validation annex (`sec:annex-screen`). Current
phrasing: "Spearman ρ = 0.92, pooled across models and in-sample;
within-model signal positive but modest".

**Rationale:** Pooled in-sample ρ overstates the screen; the within-model
signal is positive but modest. CI keeps the conditional-negative guard
(unqualified ρ = 0.92 in the conclusion fails); the exact caveat wording is
free.

**Originating ticket:** 0532 (round 2); demoted from CI by 0557.

**Status:** active

## rho-caveat-discussion

**Decision:** If the Discussion cites ρ = 0.92, the existence-proof
qualification accompanies it ("an existence proof rather than a validated
detector, as the cutoffs were tuned on the same 70 runs").

**Rationale:** The threshold rule was tuned on the same 70 runs it rejects
from — presenting it as a validated detector would be an overclaim. CI keeps
the conditional-negative guard ("existence proof" and an in-sample marker
must accompany ρ = 0.92 in the Discussion); the phrasing is free.

**Originating ticket:** 0532 (round 2); demoted from CI by 0557.

**Status:** active

## binding-constraint-conjecture

**Decision:** The binding-constraint claim ("the binding constraint is the
data, not the model") is framed as a conjecture everywhere, never as a
finding. The conclusion opens it with "the evidence points toward a
conjecture about why" and keeps the recommendation conditional ("If the
constraint is indeed the documents, …"). The abstract does not carry the
claim at all (2026-06-12 rewrite).

**Rationale:** The claim rests on the exploratory, unregistered documents
condition (one corpus, four agents, single-query only) — conjecture is the
honest register. CI keeps the negatives: the claim is forbidden in the
abstract, and any body sentence stating "binding constraint is" must carry
conjecture/conditional framing.

**Originating ticket:** 0532; demoted from CI by 0557.

**Status:** active

## equalisation-hedge

**Decision:** The equalisation paragraph (§exp2, documents condition) hedges
the constraint-relocation claim with an epistemic marker — current phrasing
"it suggests the binding constraint lies in document quality rather than
model capability, without resolving it".

**Rationale:** Scoped divergence (ticket 0541): the body speaks
within-experiment with light epistemic markers so a later edit cannot
silently revert to a flat factual register. CI keeps the sentence-scoped
negative: any sentence containing "binding constraint lies" must contain
"suggest"/"appear".

**Originating ticket:** 0541; demoted from CI by 0557.

**Status:** active

## fusion-hedge

**Decision:** The constraint-shift claim (annex-fusion architecture
paragraph) is hedged — current phrasing "the binding constraint appears to
shift from model capability to document quality".

**Rationale:** Same scoped-divergence policy as equalisation-hedge; the
shift is observed in one exploratory condition. CI keeps the sentence-scoped
negative: any sentence claiming a constraint shift must carry
"appear"/"may"/"suggest".

**Originating ticket:** 0541; demoted from CI by 0557.

**Status:** active

## novelty-benchmark-gap

**Decision:** Surviving novelty claim (1): the benchmark gap, stated in
§fusion — current phrasing "To our knowledge, no published benchmark or
system targets open-world enumeration of a national asset class with
per-cell provenance at this granularity."

**Rationale:** One of exactly three primacy claims the author kept (ticket
0532 demoted the MoE-non-determinism, day-scale-drift, and cost-F1 claims).
Epistemic-humility register mandatory ("to our knowledge", never "nobody
has done"). CI keeps a loose guard (≥2 primacy-marker sentences in §fusion);
the wording is free.

**Originating ticket:** 0532; demoted from CI by 0557.

**Status:** active

## novelty-provenance-temporality

**Decision:** Surviving novelty claim (2): the conjunction of per-cell
provenance with per-cell temporal validity, stated in §fusion — current
phrasing "Nor did we find a published demonstration of the conjunction of
per-cell provenance with per-cell temporal validity in LLM-augmented
inventories".

**Rationale:** Same kept-three policy and humility register as
novelty-benchmark-gap; counted by the same §fusion loose guard.

**Originating ticket:** 0532; demoted from CI by 0557.

**Status:** active

## novelty-two-grain

**Decision:** Surviving novelty claim (3): the two-grain scoring design,
stated in the Discussion — current phrasing "the run-level screen rates
*information credibility* while the model-level grade rates *source
reliability*" (STANAG 2511 Admiralty vocabulary).

**Rationale:** Same kept-three policy. CI keeps the loose anchor that both
STANAG terms ("information credibility", "source reliability") appear in
the Discussion — fixed external terminology, not authorial prose; the
surrounding sentence is free.

**Originating ticket:** 0532; demoted from CI by 0557.

**Status:** active

## status-vocab-mismatch

**Decision:** The status-vocabulary mismatch is explained where status
accuracy is discussed (§exp1): models answering from memory do not use the
GEM controlled vocabulary, and the grouped ~38% Proposed share mechanically
depresses measured status accuracy. Current anchors: "controlled
vocabulary", "status accuracy".

**Rationale:** Without this sentence the low status-accuracy numbers read
as model failure when part is vocabulary mismatch plus stratum composition.
CI keeps only the mechanical check (the ~38% share re-derived from
`tab_status_difficulty.tex` must appear in the body); the explanatory
phrasing is free.

**Originating ticket:** 0532 round 2 (table citation), 0511; phrase anchors
demoted from CI by 0557.

**Status:** active

## frontier-result-abstract

**Decision:** The abstract leads with the difficulty result and names the
frontier-agent finding — the paper's lead claim is that frontier agents
with web access fall short on the measured quality dimensions.

**Rationale:** Author brief (reading 1): the frontier result is what a
general reader takes away. CI keeps a loose topical check
("frontier"/"sota" in the abstract, `test_manuscript_structure.py`) — kept
in CI as a loose positive because the lead claim is structural, not
phrasing.

**Originating ticket:** 0532; recorded here by 0557 (CI check unchanged).

**Status:** active

## rho-value-static

**Decision:** The ρ = 0.92 value itself is hand-typed in the manuscript
(not macro-generated). If the screen analysis is re-run and ρ changes, every
occurrence (Discussion, conclusion, annex-screen) must be updated manually.

**Rationale:** `test_manuscript_structure.py` pins "0.92" as a fixed
empirical value; the conditional caveat guards in
`test_manuscript_cohort_and_caveats.py` key on the literal "ρ = 0.92".
A silent re-derivation would leave stale prose — this entry is the reminder
the value is static.

**Originating ticket:** 0531/0532; recorded here by 0557 (CI checks
unchanged).

**Status:** active

## built-fleet-pipeline-tail

**Decision:** The Wikipedia-seeding paragraph keeps the built-fleet vs
pipeline-tail coverage caveat: the group-seeded lists cover the *built*
fleet (92%), not the pipeline tail — no overclaim that every plant was
visible to every model.

**Rationale:** Scientific-accuracy caveat (prevents "Wikipedia covers all
177" misreading), not editorial framing — therefore KEPT in CI
(`test_wikipedia_seeding_date_matches_provenance`) as a low-risk factual
descriptor pair; recorded here so the review panel knows the phrase pair is
load-bearing.

**Originating ticket:** 0511; triaged keep-in-CI by 0557.

**Status:** active

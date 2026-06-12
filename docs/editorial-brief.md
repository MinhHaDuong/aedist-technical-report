# Editorial brief — standing editorial decisions

Standing editorial decisions for `slides/manuscript/main.tex`. CI enforces
only mechanical checks and *negative* guards (forbidden phrasings); the
positive intent behind each decision lives here and is checked at review
time by the `/review-pr-prose` panel against every manuscript diff (CI test
polarity rule, `.claude/rules/writing.md`, ticket 0557).

Entry format: one H2 per decision, slug-style heading, with
**Decision:** / **Rationale:** / **Ticket:** / **Status:**. The first
three fields are the schema the `/review-pr-prose` brief auditor
consumes; **Status:** is bookkeeping local to this file. A decision is
retired by flipping **Status:** to `retired (reason)`, never by
deleting the entry.

## lifecycle-scope

**Decision:** The abstract disambiguates the 177-plant register as spanning
the whole project lifecycle (proposed, planned, operating, cancelled,
retired) — it must never read as an operating-only register.

**Rationale:** "177 plants" without the lifecycle scope invites comparison
with operating-fleet counts (~50–60 plants) and makes the benchmark look
inflated. CI keeps the negative guard ("operating plants" /
"operating-only" forbidden in the abstract); the positive wording is free.

**Ticket:** 0532 (round 2, author reading-1 brief); demoted from
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

**Ticket:** 0532 (round 2); demoted from CI by 0557.

**Status:** active

## rho-caveat-discussion

**Decision:** If the Discussion or the screening subsection (label
`sec:ext-screen`; the screen prose moved there from the Discussion in the
0562 restructure) cites ρ = 0.92, the existence-proof qualification
accompanies it ("an existence proof rather than a validated detector, as
the cutoffs were tuned on the same 70 runs").

**Rationale:** The threshold rule was tuned on the same 70 runs it rejects
from — presenting it as a validated detector would be an overclaim. CI keeps
the conditional-negative guard ("existence proof" and an in-sample marker
must accompany ρ = 0.92 in the Discussion); the phrasing is free.

**Ticket:** 0532 (round 2); demoted from CI by 0557.

**Status:** active

## binding-constraint-conjecture

**Decision:** The binding-constraint claim ("the binding constraint is the
data, not the model") is framed as a conjecture everywhere, never as a
finding. The conclusion opens it with "the evidence points toward a
conjecture about why" and keeps the recommendation conditional ("If the
constraint is indeed the documents, …"). The abstract does not carry the
claim at all (2026-06-12 rewrite).

**Rationale:** The claim rests on the documents condition (one corpus,
four agents, single-query only) — conjecture is the honest register.
CI keeps the negatives: the claim is forbidden in the abstract, and any
body sentence stating "binding constraint is" must carry
conjecture/conditional framing.

**Ticket:** 0532; demoted from CI by 0557.

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

**Ticket:** 0541; demoted from CI by 0557.

**Status:** active

## fusion-hedge

**Decision:** The constraint-shift claim (architecture paragraph in the
subsection labelled `sec:ext-system`, promoted out of `sec:annex-fusion`
by the 0562 restructure) is hedged — current phrasing "the binding
constraint appears to shift from model capability to document quality".

**Rationale:** Same scoped-divergence policy as equalisation-hedge; the
shift is observed in the documents condition only. CI keeps the sentence-scoped
negative: any sentence claiming a constraint shift must carry
"appear"/"may"/"suggest".

**Ticket:** 0541; demoted from CI by 0557.

**Status:** active

## novelty-benchmark-gap

**Decision:** Surviving novelty claim (1): the benchmark gap, stated in
the section labelled `sec:fusion` — current phrasing "To our knowledge, no
published benchmark or system targets open-world enumeration of a national
asset class with per-cell provenance at this granularity."

**Rationale:** One of exactly three primacy claims the author kept (ticket
0532 demoted the MoE-non-determinism, day-scale-drift, and cost-F1 claims).
Epistemic-humility register mandatory ("to our knowledge", never "nobody
has done"). CI keeps a loose guard (≥2 primacy-marker sentences in the
section labelled `sec:fusion`); the wording is free.

**Ticket:** 0532; demoted from CI by 0557.

**Status:** active

## novelty-provenance-temporality

**Decision:** Surviving novelty claim (2): the conjunction of per-cell
provenance with per-cell temporal validity, stated in the section labelled
`sec:fusion` — current phrasing "Nor did we find a published demonstration
of the conjunction of per-cell provenance with per-cell temporal validity
in LLM-augmented inventories".

**Rationale:** Same kept-three policy and humility register as
novelty-benchmark-gap; counted by the same loose guard on the section
labelled `sec:fusion`.

**Ticket:** 0532; demoted from CI by 0557.

**Status:** active

## novelty-two-grain

**Decision:** Surviving novelty claim (3): the two-grain scoring design,
stated in the screening subsection (label `sec:ext-screen`; moved out of
the Discussion by the 0562 restructure) — current phrasing "the run-level
screen rates *information credibility* while the model-level grade rates
*source reliability*" (STANAG 2511 Admiralty vocabulary).

**Rationale:** Same kept-three policy. CI keeps the loose anchor that both
STANAG terms ("information credibility", "source reliability") appear in
the section labelled `sec:ext-screen` — fixed external terminology, not
authorial prose; the surrounding sentence is free.

**Ticket:** 0532; demoted from CI by 0557.

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

**Ticket:** 0532 round 2 (table citation), 0511; phrase anchors
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

**Ticket:** 0532; recorded here by 0557 (CI check unchanged).

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

**Ticket:** 0531/0532; recorded here by 0557 (CI checks
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

**Ticket:** 0511; triaged keep-in-CI by 0557.

**Status:** active

## annex-quote-anchor

**Decision:** The Annex baseline-prompt quote reproduces the as-sent
Doc-07 prompt faithfully, including the sentences "primary-sourced
reference inventory" and "Actual or expected commercial operation date".

**Rationale:** Content fidelity of a fixed external document, not
authorial prose — the annex quotes what was actually sent to the models,
so the verbatim anchors are KEPT in CI
(`test_annex_baseline_prompt_carries_as_sent_status_vocabulary`,
`test_annex_carries_doc07_prompt_verbatim_anchors`). Recorded here so a
reviewer rewording the annex framing knows the quoted block itself is
immutable.

**Ticket:** 0511; triaged keep-in-CI by 0557.

**Status:** active

## intro-contributions-runin

**Decision:** §1 closes with the contributions woven into prose (author
intro restructure, 2026-06-12, PR #1023); the earlier bold
"Contributions." run-in label with a three-item list (0513) is no longer
pinned. CI keeps only the negative guard: contributions never get their
own section heading.

**Rationale:** Authorial phrasing/structure choice — positive pin
demoted per the CI polarity rule (0557). The framing history lives here,
not in a test.

**Ticket:** 0513; demoted during PR #1023 gate (residual missed by 0559
sweep, which covered test_manuscript_0512_structure.py only).

**Status:** active

## label-stability-contract

**Decision:** Every `\label{}` name in `slides/manuscript/main.tex`
(`sec:intro`, `sec:fusion`, `sec:discussion`, `sec:annex-*`, …) stays
attached to its content as that content moves through restructures. Tests
and this brief anchor on labels — never on section numbers, annex letters,
titles, or adjacency. Renaming or dropping a label is a contract change
that must update every anchored test and brief entry in the same PR.

**Rationale:** The back-half restructure (tracking ticket 0560) retitles,
renumbers, and reorders sections; labels are the only structural
identifiers that survive such moves. Label-keyed extraction
(`manuscript_source.section()`, ticket 0561) makes the restructure PRs
CI-safe without weakening any guard.

**Ticket:** 0560 (contract recorded); anchors re-keyed by 0561.

**Status:** active

## no-companion-paper-promise

**Decision:** The main text promises no future publication: no "companion
paper", no "follow-on paper", no "planned cross-evaluation". Work not
reported in this paper is framed as future work in the research programme
(the numbered Future research section, label `sec:future`) or as
not-measured-here scoping, never as a commitment to a specific
forthcoming paper. (Ticket 0563 stripped the Temporality annex's
"subsequent paper" sentence; the decision now covers the full manuscript,
annexes included.)

**Rationale:** Publication promises age badly, bind the authors to titles
and scopes that drift, and add nothing a "future work" framing does not.
The 0560 restructure created the Future research section precisely so that
forward-looking material reads as programme, not promise.

CI negative guard:
`test_manuscript_0512_structure.py::test_no_companion_paper_promise_in_body`
bans the promise phrasings across the full body — no carve-out (the
Temporality exemption was removed when ticket 0563 stripped its sentence).

**Ticket:** 0562, 0563 (tracker 0560).

**Status:** active

## plausible-text-generator

**Decision:** The "plausible-text generator" phrase (0513 reframing of
"random words generator") is no longer pinned positively; the abstract
rewrite (PR #1023) rephrased it. CI keeps the negative guard:
"random words generator" never returns.

**Rationale:** Same polarity-rule demotion as above.

**Ticket:** 0513; demoted during PR #1023 gate.

**Status:** active

## kb-programme-items

**Decision:** The Future-research programme names the three
knowledge-base design items at no-spoiler altitude: the
representation-authority tension (narrative asset page vs knowledge
graph vs append-only claim log of which both are projections, with
this benchmark as the arbiter), the extract-once/render-many asymmetry
principle (text→structure is the measured lossy direction;
structure→text is cheap), and the bitemporal/modal claim log covering
plans, forecasts, and scenario projections. The topology analysis and
the modal model stay in `docs/kb-design-note.md` — the manuscript only
names the questions.

**Rationale:** 0560 restructure discussion + `docs/kb-design-note.md`
(2026-06-12 Imagine session, §7). Per the CI polarity rule, no positive
CI assertion pins the wording — this entry is the guard, checked by the
review panel against manuscript diffs.

**Ticket:** tickets/0565-future-research-kb-design-items-insert.erg

**Status:** active

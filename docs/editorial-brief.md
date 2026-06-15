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

**Decision:** Retired. The conclusion no longer presents the Spearman ρ
screen correlation at all — ticket 0598 dropped the ρ regression from the
whole manuscript (body and annex). The screening conclusion (a
reference-free reliability grade triages the weak models without ground
truth) is now carried by Figure~\ref{fig:reliability} and its in-sample
existence-proof caveat, not by a coefficient. There is no ρ claim left to
police.

**Rationale:** This entry existed only to keep the in-sample caveat
attached to the conclusion's ρ = 0.92 citation. With the citation gone the
guard is moot. The companion conditional-negative CI guard was removed in
lockstep (ticket 0598).

**Ticket:** 0532 (round 2); demoted from CI by 0557; retargeted to
`fig:reliability` by 0586; retired by 0598.

**Status:** retired

## rho-caveat-discussion

**Decision:** Retired. The Discussion / external-screening subsection no
longer cites ρ = 0.92 — ticket 0598 dropped the ρ regression from the
whole manuscript. The existence-proof / in-sample framing the screen prose
needs survives on its own terms ("an existence proof rather than a
validated detector, as the cutoffs were tuned in-sample"); it is no longer
tethered to a ρ value.

**Rationale:** The entry existed only to keep the existence-proof
qualification attached to the Discussion's ρ = 0.92 citation. With the
citation gone the guard is moot. The companion conditional-negative CI
guard was removed in lockstep (ticket 0598).

**Ticket:** 0532 (round 2); demoted from CI by 0557; Annex E reference
retargeted to `fig:reliability` by 0586; retired by 0598.

**Status:** retired

## binding-constraint-conjecture

**Decision:** The binding-constraint claim ("the binding constraint is the
data, not the model") is framed as a conjecture everywhere, never as a
finding. The conclusion no longer opens with the conjecture sentence at all
(dropped by ticket 0586 as vague generality; replaced with the
documents-equalisation evidence — Mistral Large ≈ Opus with documents — and
a conditional sourcing recommendation). The recommendation stays conditional
("If the constraint is indeed the documents, …"). The abstract does not
carry the claim at all (2026-06-12 rewrite).

**Rationale:** The claim rests on the documents condition (one corpus,
four agents, single-query only) — conjecture is the honest register, and
the bare conjecture sentence in the conclusion was vague generality the
measured equalisation result states more concretely. CI keeps the
negatives: the claim is forbidden in the abstract, and any body sentence
stating "binding constraint is" must carry conjecture/conditional framing.

**Ticket:** 0532; demoted from CI by 0557; conclusion sentence dropped by
0586 (abstract ban retained).

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

**Decision:** The ρ = 0.92 value was hand-typed in the manuscript until
ticket 0566 macro-sourced it: every occurrence now flows from
`\ScreenPooledSpearman` in `macros_screen_validation.tex`, recomputed by
`screen_validation_within_model.py` from the runs data. A re-run that
shifts ρ updates the prose through the fragment rebuild; the conditional
caveat guards keep firing because they assert on macro-expanded text.

**Rationale:** the hand-typed value was the last manuscript number outside
the numbers-through-macros rule (ticket 0531). `test_manuscript_structure.py`
now guards the macro call; `test_manuscript_macros.py` drift-checks the
macro against the co-generated CSV artifact.

**Ticket:** 0531/0532; recorded here by 0557; retired by 0566.

**Status:** retired (macro-sourced by ticket 0566)

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

**Decision:** The Annex analysis-cohort prompt quote reproduces the
as-sent Doc-07 prompt faithfully (the boxed `promptbox` reformat is
typographic only). The archived-baseline prompt block was deleted
(reading-2 finding 9, ticket 0590) — its results were never presented.

**Rationale:** Content fidelity of a fixed external document, not
authorial prose — the annex quotes what was actually sent to the models,
so the verbatim anchors of the kept Doc-07 prompt are KEPT in CI
(`test_annex_carries_doc07_prompt_verbatim_anchors`,
`test_analysis_cohort_prompt_matches_shipped_record`). The deleted
archived-baseline block is now negatively guarded
(`test_annex_baseline_prompt_block_removed`). Recorded here so a reviewer
rewording the annex framing knows the quoted prompt itself is immutable.

**Ticket:** 0511; triaged keep-in-CI by 0557; baseline block removed by 0590.

**Status:** active

## intro-contributions-runin

**Decision:** §1 contributes a single thing — THE BENCHMARK — woven
into prose, never a three-contributions-plus-three-results enumeration
(reading-2 finding 27, ticket 0580). The four-dimension quality score
is presented as the benchmark's computable metric, not as a separate
contribution. The intro drops the two-grain credibility/reliability
framing and the STANAG 2511 / NATO Admiralty vocabulary (those live in
the screening subsection `sec:ext-screen`, pinned by entry
novelty-two-grain) and drops the "targeted pipeline design narrows the
gap" framing. The screening message reads as "reference-free criteria
suffice to screen out the weakest runs and models". The earlier bold
"Contributions." run-in label with a three-item list (0513) is no
longer pinned. CI keeps only the negative guard: contributions never
get their own section heading.

**Rationale:** Authorial phrasing/structure choice — positive pins
demoted per the CI polarity rule (0557). One-contribution framing reads
as a focused benchmark paper rather than a checklist; the framing
history lives here, not in a test.

**Ticket:** 0580 (one-page benchmark rework); 0513 (earlier run-in
demotion during PR #1023 gate).

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

## text-and-captions-standalone

**Decision:** The main text AND the figure/table captions are standalone at
the maths/ideas level: no code references — file paths, module/function/script
names, config keys, filenames — appear in §1–§9, the Conclusion, the
backmatter, or any caption among them (everything before `\appendix`).
Load-bearing implementation detail is relocated to the relevant annex and
reached by `\ref{sec:annex-…}`. Code references are allowed only in the
annexes (after `\appendix`). This SUPERSEDES ticket 0591's caption exemption:
0591 cleaned §1–§9 prose but excised `\caption{…}` blocks from its scan; 0633
brings captions into scope. Carve-out — reader-facing data tokens that are not
repo artifacts stay (the OpenStreetMap `power=plant` tag, the Wikipedia
revision id, the controlled status vocabulary).

**Rationale:** A reader of the paper and its captions should follow the
ideas without consulting the codebase; repo artifacts are an annex concern.
Canonical re-articulation of finding 22 (author, 2026-06-15). CI keeps the
negative class guard
(`test_manuscript_0633_caption_coderefs.py`): code-reference signatures are
forbidden in body captions and in the body before `\appendix`; the annexes are
out of scope. The 0591 caption-exempting guard
(`test_manuscript_codenames_coderefs.py`) remains for the §1–§9 prose scope it
already covered.

**Ticket:** tickets/0633-global-caption-sweep-text-and-captions-s.erg
(supersedes ticket 0591's caption exemption)

**Status:** active

## three-scoring-levels-perpendicular

**Decision:** The three scoring levels in §discussion ("A result is scored at
three levels") are genuinely perpendicular axes — process, output, source. In
particular, \emph{method quality} is a property of the *process*, not of any
output it produces: whether the procedure is auditable, reproducible, and
cost-predictable independent of which model runs it (the definition set at the
end of §ext-system). It must NOT be defined through the quality of the table
the method returns. The cost-versus-F1 figure *relates* method cost to result
(run/table) quality across two distinct axes; it does not *define* method
quality as table quality. Run quality scores one output table; model quality
aggregates runs into a source-reliability grade.

**Rationale:** Reading-2 finding 40 (author, 2026-06-14): the prior wording
defined method quality as the cost-vs-table-quality relation while also
defining run quality as the quality of one table, so the two shared the
table-quality axis and "perpendicular" was internally inconsistent. The
method/model distinction was already established at the end of §ext-system;
§discussion builds on it rather than re-conflating. The three-quality spine of
the paper (data / answer / method) treats method quality as a distinct axis,
not a function of answer/table quality.

**Ticket:** tickets/0599-discussion-section-conflates-method-qual.erg

**Status:** active

## scoring-annex-v0-1

**Decision:** The four-dimension quality score is delivered as a dedicated
Scoring annex (`sec:annex-scoring`), the FIRST `\appendix` section (Annex A),
which owns figure S1 (`fig:quality-floor`). It writes out, in order, the
cell--run--model hierarchy and each dimension's formula (q1 accuracy = F1,
q2 coherence, q3 provenance, q4 temporality), transcribed to match the code
(`score_mechanical.py`, `score_coherence_level.py`, `metrics.py`). It is
marked version 0.1 of the benchmark, to be improved. §3 (`sec:quality`)
references it as THE IMPLEMENTATION ("the scoring is implemented in …"),
never as a "detail". Cost/run-bookkeeping detail stays in the Exp1 annex
(it scores method quality, not the benchmark's run/model output); the
reliability-gate sensitivity sweep also stays in the Exp1 annex
(gate-robustness diagnostic, not the benchmark definition).

**Rationale:** Ticket 0602 (author, 2026-06-15). The intro promised a
four-dimension score whose math the body delivered only qualitatively;
the annex makes the promise resolve to real formulas aligned to the
scorer. Scoring is Annex A because it delivers the promised benchmark
(semantic ordering); figure numbering follows, keeping the quality-floor
heatmap as S1. The benchmark does NOT measure corroboration (no
`corroborat*` in `src/aedist/score_*.py`), so the intro's "and
corroboration measured" claim was dropped; the Exp2 sections retain
"corroboration" where they legitimately report Source-2 double-sourcing.
The operational citation hedge ("counts and checks presence … does not
verify each cited source against each cell") moved from the intro to §3's
provenance discussion, where it scopes the verifiable-vs-verified
distinction.

**Ticket:** tickets/0602-intro-para-3-deliver-four-dimension-math.erg

**Status:** active

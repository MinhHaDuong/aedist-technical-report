# KB design note — information flow between corpus, claims, asset pages, and the statistical table

**Status:** working design note, output of the 2026-06-12 Imagine session
(post-conference discussion). Feeds the Future-research programme of the
manuscript (ticket 0562, two–three sentences at no-spoiler altitude) and the
follow-on system paper. Not citable from the manuscript bibliography
(writing rule: no in-repo documents in the references).

## 1. Product constraints

- **One narrative page per asset** (power plant / power center), GEM-style,
  in all cases. The page is the human audit interface and the only container
  for what no schema holds: contested status discussions, plan-cycle
  history, multilingual naming, developer changes.
- Precision that pins the design: pages are required for **auditability and
  contribution** (method quality), not for deriving the statistical table.
  The table must not depend on re-extracting facts from prose.
- The statistical table is a **dated projection**: T1 snapshot currency now,
  T2 historical reconstructability ("the fleet as of 2018") eventually.

## 2. Design space: four topologies

Four artifact kinds: source corpus documents, structured claims (KG), asset
pages, statistical table. The realistic flows:

```
A. Page-centric (GEM's process)      B. KG-centric (claim-first)
   corpus → pages → KG → table          corpus → KG → pages
                                                 KG → table

C. Dual-authority (Wikipedia+Wikidata)  D. Log-centric (accounting)
   corpus → pages ⇄ KG → table             corpus → claim log → KG → table
            (reconciliation forever)                claim log → pages
                                           (edits/verifications append to log)
```

Elimination arguments:

- **A is eliminated by our own measurements.** Its load-bearing edge is
  pages → KG: facts live in prose first and are extracted into structure.
  That step is exactly the articulation failure mode and the matcher-as-NER
  instrument limit the paper quantifies — and a page-authoritative store
  pays the tax on every derivation, forever.
- **GEM is not a counterexample.** GEM's pages work because the same human
  researcher writes the page and curates the tracker row in the same act —
  topology C with reconciliation done in the author's head at write time.
  That labor model does not scale to the under-documented long tail, which
  is our motivating setting. "Like GEM" is right as *product* spec (one
  page per asset), wrong as *process* spec.
- **C institutionalises reconciliation.** Wikipedia⇄Wikidata divergence is
  the documented steady state; the bot ecosystem managing it is the
  permanent maintenance bill. Not with a staff of zero.
- **B vs D is the state-vs-event choice** (see §5): B keeps current values
  and treats history as revisions; D makes an append-only claim log
  authoritative and derives everything. D buys T2 reconstructability,
  audit, and a clean edit discipline at a higher engineering cost. §6 gives
  a staging that defers most of that cost.

## 3. The asymmetry principle

The one design lesson the experiments license directly:

> **Text→structure is the lossy, hard direction (measured); structure→text
> is cheap and reliable. Do the hard direction once, at ingest, against
> source documents; do the easy direction many times, at render.**

Corollaries: claims are extracted from corpus documents (not from pages);
pages are rendered from claims; the table never re-extracts from prose.

## 4. Information flow (topology D)

```
        harvest (per country × subsector)
corpus docs ──LLM claim extraction──▶ claim log (append-only: s,p,o + citation
   ▲                                      span + times + modality + author)
   │                                          │ fold/consolidate (conflict
   │                                          ▼  resolution HERE, with full
   │                                   KG (current state)      provenance)
   │                                    │            │ render
   │                              project(date,     ▼
   │                               world)        asset pages (audit UI;
   └── gap-driven harvest tasks ◀── table         corrections append to log)
       (LP bounds vs control totals;
        sparse recognition-matrix rows)
```

- Conflict resolution does not disappear; it is **located** — at fold time,
  with every competing claim and its source in hand. That is where LLM
  reasoning adds value (the annex's hard cases) and where the
  human-in-the-loop vets the authentic hard statistical questions.
- Humans and LLM verifiers never patch a projection; they append a
  correction or verification event and the projections regenerate — the
  repo's own "fix the master, regenerate, never patch downstream"
  discipline applied to the knowledge base.
- The **feedback edge** closes the loop: the estimation layer (LP bounds
  against control totals, capture–recapture residuals, sparse
  recognition-matrix rows) generates the harvest queue. Harvesting is
  per-subsector by construction (genericity rule), so divide-and-conquer
  querying is the system's native mode.

## 5. Claims vs events: the temporal-modal model

Unifying rule: **every log entry is an assertion event** — transaction
time, source document, citation span — whose payload is a claim. Claims
carry a **modality**, and the fold rules differ by modality:

| Modality | Example | Folds into |
|---|---|---|
| Attribute claim | "capacity = 1200 MW" (valid interval) | current state (KG, table) |
| Occurrent (world event) | groundbreaking on 2029-06-01 | lifecycle state transitions |
| Institutional act | PDP8 authorizes X | institutional status (proposed / planned / cancelled rungs) |
| Forecast | PDP8 expects commissioning 2028–2029 | "current expectation" view per author; superseded chain; **resolved by occurrents** |
| Scenario projection | in scenario A by institution I, X built 2031 | scenario-conditional views only; **never** actual state |

Three time axes, plus a context axis:

- **transaction time** — when we assimilated the claim (audit,
  reproducibility);
- **assertion/issue time** — when the source asserted it (orders
  supersession among forecasts and plan revisions);
- **valid/target time** — when the claimed thing holds (attribute
  intervals, occurrent dates) or is projected to occur (forecast and
  scenario targets);
- **world context** — `actual`, or a named scenario world
  `(institution, scenario-id, vintage)`. Scenario claims are conditional
  on their assumption set — scenarios are explorations, not predictions
  (standard IAM discipline) — so they never resolve against reality and
  never fold into the actual register.

### Worked examples (from the 2026-06-12 discussion)

**"PDP8, published 2024, authorizes X and forecasts commissioning
2028–2029."** One source span, three log entries of three modalities:

1. occurrent: `publication(PDP8)`, valid 2024 — the administrative act
   itself happened;
2. institutional act: `authorization-granted(X, by=PDP8)`, effective 2024 →
   folds: `status(X) = planned/authorized` as of 2024;
3. forecast: `commissioning(X)`, target 2028–2029, author = PDP8, issued
   2024 → folds into the official-expectation view; superseded by any later
   plan revision.

The decomposition of one sentence into modality-tagged claims is a language
task — another place the LLM earns its keep at ingest.

**"In scenario A by institution I, project X is built in 2031."**

4. scenario projection: `commissioning(X)`, target 2031, world =
   `(I, scenario-A, vintage)` → visible only in scenario-A projections,
   e.g. `table(2031, world=scenario-A)`; absent from the register.

**"Groundbreaking occurred on 2029-06-01"** (reported by source S,
assimilated 2029-07):

5. occurrent: `construction-start(X)`, valid 2029-06-01, source S,
   transaction 2029-07 → folds: `status(X) = under-construction` from
   2029-06-01 — **and resolves forecast (3)**: realised late against the
   2028–2029 window. The resolution edge is itself data: a
   forecast-realisation ledger (plan-cycle realisation rates) falls out of
   the model as a research by-product.

### Projections

- `table(date, world=actual)` — the statistical register (T1 now, T2 by
  log replay);
- `table(date, world=scenario)` — scenario pipeline tables from the same
  machinery;
- `page(asset)` — renders all modalities as prose sections: current
  status, lifecycle history, plans & projections, contested points.

### Tie-back to the benchmark

The status-composition finding says benchmark difficulty concentrates in
proposed plants — precisely the institutional and prospective modalities.
The hard tail of the task is the part that needs this machinery; models
answering from memory fail worst exactly where representation is hardest.
The benchmark also arbitrates the b/-tension empirically: build both a
page-authoritative and a claim-authoritative state from the same harvested
corpus, derive the table from each, score both with the same LP matcher
against the same reference.

## 6. Staging (CIRED-sized MVP)

Defer the event store, keep the discipline:

- one structured **claims file per asset** (citation spans, modality,
  times) + one **rendered page**, in a git repository;
- **git history is the transaction-time log for free** — append-only by
  convention, diffable, blameable;
- the table is a Makefile artifact projected from the claims files;
- migration to a real event store / graph store is monotone (files →
  store) if and when the claim files prove out; never a rewrite.

## 7. What enters the manuscript now

Two–three sentences in the Future-research programme (ticket 0562):

1. the authority question — asset page, knowledge graph, or an append-only
   claim log of which both are projections — with the page⇄graph edge
   direction open and this benchmark as the arbiter;
2. the extract-once/render-many asymmetry principle, as the design lesson
   the articulation findings support;
3. the T2 item recast as a bitemporal claim log whose modality layer covers
   plans, forecasts, and scenario projections (occurrents fold into state;
   scenario claims stay context-qualified).

Nothing further — the topology analysis and the modal model are follow-on
paper material.

## 8. Open questions

- Claim granularity (one claim per cell? per sentence? negation and
  retraction semantics?).
- Authority ordering among sources (adopted plan > draft > press) and its
  interaction with the supersession chain.
- Cross-source entity resolution: the matcher-as-NER problem recurs at
  ingest (which X is this claim about?) — the LP matcher work is reusable.
- Page-edit round-trip UX: how a human correction on the rendered page
  becomes a log event with minimal friction.
- When the consolidated state needs a real graph store rather than files.
- Schema evolution of the claim model without log rewrites.

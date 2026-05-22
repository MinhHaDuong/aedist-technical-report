# Protocol — Doc 03: Example dialogue

This document walks through one Phase A + Phase B session end to end. Agent responses are abridged to keep the document readable; user-side messages are reproduced verbatim.

Companion documents:
- Doc 01 — The ask (review framing + verdict format)
- Doc 02 — Phase A meta-prompt (verbatim) — this dialogue abridges it; the full bytes the agent receives are there
- Doc 04 — Implementation (state machine, variables, classifier, budget axes, tools, artefacts)
- Doc 05 — Experiment (subject selection, design rationale, future work, FAQ on the ask)
- Doc 06 — Validation round 1 (per-reservation changelog: what changed since round 1)

---

## Phase A — turn 1 (user side)

The initial query is Doc 02.

## Phase A — turn 2 (agent response, example, abridged)

```json
{
  "system_prompt": "You are a senior energy analyst with deep knowledge of South-East Asian power-sector planning, primary-source research methodology, and structured inventory production. Prefer primary government documents over secondary aggregators. When citing a source, attach a specific URL and a relevant excerpt or page reference.",
  "designed_prompt": "Produce a comprehensive inventory of Vietnam thermal power plants > 30 MWe. Use web search to locate primary planning documents, official utility reports, and regulator decisions. Structure your output as: (1) Sector overview ... (2) Per-plant narratives ... (3) Structured table with the columns listed in the task ... (4) Cross-tabulations ... (5) Annotated bibliography ...",
  "settings": {
    "thinking": true,
    "max_tokens": 16000,
    "rationale_for_settings": "Thinking enabled because the verification pass needs cross-row consistency reasoning. Max tokens high enough to produce the table + narratives in one polished pass."
  },
  "rationale": "Targets accuracy by mandating primary-source preference; coherence by requiring cross-tabulations that must reconcile with the main table; provenance by the dedicated source columns + bibliography; temporality by the as-of date requirement on each row."
}
```

---

## Phase B — turn 1 (user side)

The agent's own `designed_prompt` from the Phase A turn 2 example above is sent verbatim, no status prefix on this first turn:

> Produce a comprehensive inventory of Vietnam thermal power plants > 30 MWe. Use web search to locate primary planning documents, official utility reports, and regulator decisions. Structure your output as: (1) Sector overview ... (2) Per-plant narratives ... (3) Structured table with the columns listed in the task ... (4) Cross-tabulations ... (5) Annotated bibliography ...

## Phase B — turn 1 (agent response, example, abridged)

The agent produces a *planning preamble* — describes its intended search strategy, decomposes the task into sub-questions, identifies likely primary-source pools, lists a few candidate searches. No structured inventory yet. ~800 tokens out.

---

## Phase B — turn 2 (user side)

The harness's classifier determines that the previous response contains no report. It therefore sends an ENCOURAGE reply, prefixed by the budget status:

> Status: remaining 49.2K of 50K tokens, $2.997 of $3.00. Verify pending.
>
> Proceed as you think is best in autonomous agentic mode.

(The ENCOURAGE string is verbatim, the same on every encouragement turn.)

## Phase B — turn 2 (agent response, example, abridged)

The agent executes the planned search, fetches several primary documents, produces:
- Sector overview (~1500 tokens)
- A structured table with ~40 rows, source URLs populated where confidence is high, empty where it is low
- Cross-tabulations (capacity by fuel × status, etc.)
- An annotated bibliography (~85 citations)

Total ~5000 tokens out, with 9 web_search calls and ~45K connector tokens (retrieval payload — not counted toward the 50K cap, see Doc 04 §2.3).

---

## Phase B — turn 3 (user side)

The harness's classifier determines that the previous response contains a report and that the verify pass has not yet been used. It therefore sends a VERIFY reply, prefixed by the budget status:

> Status: remaining 44K of 50K tokens, $2.79 of $3.00. Verify on this turn.
>
> Thank you for the inventory. Please now verify and polish it in ONE focused pass, prioritising: (a) per-row provenance — every Source 1 and Source 2 cell must point to a specific URL from your bibliography; (b) coverage — any entity present in your bibliography but absent from the table; (c) temporality — every row has an as-of date or status-change note; (d) internal consistency — totals reconcile across the table and the statistical summary. Return the corrected inventory only — no meta-commentary on what you changed.

(The VERIFY string is verbatim, sent exactly once per session.)

## Phase B — turn 3 (agent response, example, abridged)

The agent produces the polished inventory:
- Table corrected — every row has Source 1 and Source 2 cells populated with specific URLs.
- A few rows from turn 2 are removed because their sources didn't pass the strong-citation test.
- Two rows added that were present in turn 2's bibliography but missing from the table.
- As-of dates appended where missing.
- Totals reconciled across the statistical summary tables.

Total ~6400 tokens out, no additional web_search calls (the agent verifies against its existing bibliography).

The harness's classifier determines that the previous response contains a report, and the verify pass has now been used. The session ends; the polished turn-3 response is the final artefact.

---

## Remarks on the conversation

**Session totals.** 3 Phase B turns; total tokens out 800 + 5000 + 6400 = 12.2K (well under the 50K cap); total bill ~$0.25 (well under the $3 guard); classifier cost as harness overhead, not deducted from the agent's budget, ~$0.0005; `terminal_sent`: false (the loop closed via verify-used, not via budget). The polished turn-3 response is the deliverable scored in Phase C (cross-evaluation) and against the reference dataset.

**Paths this example does not show.** A `no_report → ENCOURAGE → no_report → ENCOURAGE → no_report → ENCOURAGE → no_report → TERMINAL` trace (the 3-encouragement exhaustion path; Doc 04 §2.4 describes it — has not arisen in the smoke runs to date). A budget-exhaustion `TERMINAL` (the 20% threshold path; the dual-axis cap is designed to be non-binding for typical sessions, but if either axis fires the harness sends TERMINAL on the next turn regardless of classification). A multi-rep cumulative trace — each agent runs 3 replications of Phase B with the same Phase A design, but each replication is independent and shares no state with the others.

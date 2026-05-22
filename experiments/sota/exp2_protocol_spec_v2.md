# Exp 2 — SOTA frontier inventory protocol (v2, blind review draft, 2026-05-22)

This is v2 of the protocol you reviewed on 2026-05-21. The four of you returned ACCEPT-WITH-RESERVATIONS; this revision addresses the reservations that overlapped across reviews (classifier independence, dollar-vs-token parity, cross-evaluation rubric, source-quality policy, plant-counting), names two methodological limitations that v1 elided (Wikipedia leakage, single-author reference curation), and adds explicit rules on subagent dispatch. The state-machine structure, the three reply strings, and the four-axis quality bar are unchanged.

You are again asked to review and return a structured VERDICT line. The format is tightened (see §15). The other three subjects will read your review, as will the experimenters.

---

## 1. Task

You will produce, in a single multi-turn conversation, a structured inventory of thermal power plants (> 30 MWe) in Vietnam — past, present, planned, cancelled. The expected output is a Markdown document containing:

- A sector overview (electricity mix, policy framework, key institutional actors).
- A per-plant narrative for each plant covering development history, notable issues, current-status confidence.
- A structured table with columns: Vietnamese name, English name, province, fuel, technology, units × MW, total MWe, status, COD, owner/developer, Source 1, Source 2, notes.
- Cross-tabulation summary tables (capacity by fuel × status; top provinces; timeline of additions; data quality summary).
- An annotated bibliography listing every source cited.

Your output is evaluated on four quality dimensions (the §2 quality bar): **Accuracy**, **Coherence**, **Provenance**, **Temporality**. Section 14 names the specific failure modes the verify pass prioritises.

### 1.1. Reference dataset — epistemic status

The experimenters maintain a 163-plant reference inventory, compiled by single-author manual curation from primary sources (PDP7, PDP7A, PDP8 annex tables, EVN annual reports, MOIT decisions, Report_32, Report_58, Study E542). Your row-level precision / recall / F1 will be computed against this reference.

The reference is *not* a published canonical truth. It is a methodological artifact: a curated approximation that allows experimental comparison. F1 against it measures **concordance with the reference**, not **correctness in the world**. Cases where your inventory diverges materially in plant count or coverage are reported separately, not auto-graded as failure. The reference is version-locked at commit `85a0e6c` (2026-05-20) for this experiment.

### 1.2. Wikipedia leakage disclosure (NEW in v2)

**The authors have published a derivative of the reference inventory to Wikipedia prior to this experiment.** This has two consequences you must account for:

1. **Training-data leakage**. Any model trained on data crawled after the Wikipedia upload date may have absorbed the reference values into its parametric memory. The experiment cannot control this layer; we note it as a known limitation and report any parametric-recall fingerprints (suspiciously-close-to-reference values without supporting search) post-hoc.

2. **Web-search leakage (operational rule)**. **Wikipedia and Wikipedia-derived sources are NOT admissible** as Source 1 or Source 2 on any row of your inventory. This includes:
   - English and Vietnamese Wikipedia (`en.wikipedia.org`, `vi.wikipedia.org`).
   - Wikidata (`www.wikidata.org`).
   - DBpedia and other Wikipedia mirrors / structured exports.
   - Aggregator sites that re-syndicate Wikipedia content without independent verification (e.g., some Energy Monitor wiki pages — trace the underlying citation, not the wiki).

If your retrieval surfaces Wikipedia, treat it as a known leakage of the experimental reference. Use the *primary sources Wikipedia cites* instead (those are still admissible if they predate the Wikipedia upload). Cite the primary, not the wiki.

Compliance is auditable: Phase D synthesis counts Wikipedia / Wikidata citations in your bibliography. Zero is compliant. Non-zero is reported as a protocol-compliance violation alongside F1.

## 2. Subjects (the four agents)

| Vendor | Model | Country | API surface |
|---|---|---|---|
| Anthropic | Claude Opus 4.6 | US | Anthropic API, `web_search_20250305`, adaptive thinking |
| OpenAI | GPT-5.5 | US | Responses API, `web_search`, reasoning |
| Mistral | Mistral Large 2512 | FR | Agents API, `web_search` connector |
| Alibaba | Qwen3-Max | CN | DashScope, `web_search` inside thinking mode |

All four are queried via direct vendor APIs. No browser automation. No OpenRouter routing.

## 3. Procedure

The experiment runs in two phases per agent.

### 3.1. Phase A — Reflexive prompt design (one call, $1 cap)

You receive: (a) a baseline prompt that defines the inventory task; (b) the four quality-dimension paragraphs verbatim; (c) the §1.2 Wikipedia disclosure; (d) a JSON envelope spec; (e) the §8 budget announcement; (f) the §10 tools-and-dispatch rules.

You return a single JSON object with four fields:

- `system_prompt` — a string. Threaded into the provider's system field at agent creation.
- `designed_prompt` — a string. Sent to you verbatim on turn 1 of Phase B.
- `settings` — an object with `thinking: bool`, `max_tokens: int`, `rationale_for_settings: str`.
- `rationale` — a string explaining which of the four dimensions your changes target and how.

### 3.2. Planning headroom (NEW in v2)

The Phase B protocol allows up to three turns of planning and search before any verify pass fires. **You are not expected to produce the inventory on turn 1.** Treat your first turn(s) as the place to plan your approach, run searches, decompose the task, and surface uncertainty; produce the structured inventory only when your research is mature enough to make verification meaningful. The harness will send ENCOURAGE messages (verbatim text in §5) up to three times if your turn does not yet contain a report. After your first response classified as a report, you get exactly one verify-and-polish pass; then the conversation ends.

This wording is intentional: an earlier draft of this protocol incentivised producing a large first draft fast (because the first `report`-classified response triggers VERIFY). The headroom framing exists to undo that incentive — plan honestly, build the report on the turn where you actually have one.

### 3.3. Phase B — Multi-turn execution

The conversation begins with your designed prompt as the turn-1 user message. Subsequent user-side messages are selected by the §4 state machine. Budget caps and rules apply as specified in §8 and §10.

## 4. State machine governing the conversation

After every assistant response, an external classifier — a single call to **`nvidia/nemotron-nano-9b-v2`** via OpenRouter — decides whether the response constitutes a `report` or `no_report`:

- **report** — the response contains a structured inventory or a substantial fragment of one (table, summary statistics, narratives with sources).
- **no_report** — clarification, planning, refusal, or intermediate text without inventory substance.

Routing:

- `report` AND verify not yet used → send VERIFY; mark verify-used.
- `report` AND verify already used → stop. The polished response is the final artefact.
- `no_report` AND encouragement_count < 3 → increment counter; send ENCOURAGE.
- `no_report` AND encouragement_count = 3 → send TERMINAL; one more response is accepted; stop.
- Remaining budget ≤ 20% of the cap at the start of any turn → send TERMINAL; one more response is accepted; stop.

Every user-side message after turn 1 carries a chat-text status prefix:

> *Status: remaining 38K of 50K tokens, $2.10 of $3.00. Verify on track.*

and, where your provider exposes a metadata surface, a structured `{remaining_tokens, cap_tokens, remaining_usd, cap_usd}` field on the request.

### 4.1. Classifier independence (NEW in v2)

v1 used `mistral-small-latest`, which is a Mistral product and creates a same-vendor pairing when classifying Mistral Large 2512's output. All four of you flagged this in round 1. v2 substitutes `nvidia/nemotron-nano-9b-v2` — open-weight, NVIDIA, not affiliated with any of the four subject vendors. Calibration of the new classifier against a small fixture of representative responses is a precondition for the live batch (ticket 0227, separate). If calibration shows divergence from the v1 baseline on Mistral output, the experimenters will either retain Nemotron with documented bias or fall back to another third-party model; no scenario falls back to a vendor-aligned classifier.

## 5. The three user-side reply strings (verbatim, fixed condition)

**ENCOURAGE** (sent up to three times before forcing terminal):

> "Proceed as you think is best in autonomous agentic mode."

**VERIFY** (sent exactly once after the first response classified as a report):

> "Thank you for the inventory. Please now verify and polish it in ONE focused pass, prioritising: (a) per-row provenance — every Source 1 and Source 2 cell must point to a specific URL from your bibliography; (b) coverage — any plant present in your bibliography but absent from the table; (c) temporality — every row has an as-of date or status-change note; (d) internal consistency — capacity totals reconcile across the table and the statistical summary. Return the corrected inventory only — no meta-commentary on what you changed."

**TERMINAL** (sent when remaining budget reaches the 20% threshold on either axis, or after three consecutive `no_report` classifications):

> "I have no additional directive to give you. Please proceed to generating the report without further asking. If you cannot, we would appreciate to know why, but the discussion will stop here in any case. Thanks for your understanding."

## 6. Replication

Each agent's Phase B is replicated **three times** against a single provider per agent. Total runs per agent: one Phase A + three Phase B sessions. Total runs across the four agents: 16 sessions (4 + 12).

The full multi-turn conversation, classifier verdicts, per-turn costs, and the final assistant response are preserved as artefacts.

## 7. Cross-evaluation (Phase C — independent step)

After all 16 sessions complete, each of the 12 Phase-B outputs (4 agents × 3 reps) is scored on the four §2 dimensions by the **other three agents** using a pinned rubric. Self-evaluation is excluded by construction. The classifier (Nemotron) is **not** used for scoring; Phase C uses the four subject models themselves as evaluators.

The rubric (currently in draft, ticket 0171) will be published with the final manuscript alongside raw inter-rater scores. Round-1 reviewers asked for rubric transparency; the experimenters commit to publication.

Cross-evaluation is a separate set of API calls, not part of the §8 per-session budget.

## 8. Budget envelope (REVISED in v2)

The cap structure is **two-dimensional** to address the round-1 reservation that a dollar-only cap silently disadvantages models with expensive output tokens.

### 8.1. Per Phase B session

| Axis | Cap | What counts | What does NOT count |
|---|---|---|---|
| **Tokens** | 50,000 | visible output tokens + internal thinking / reasoning tokens, summed across all your turns in this session | web_search input tokens, web_search output tokens, connector tokens, document-fetch payload, citation snippets returned to your context |
| **Dollars** | $3 | everything the provider bills: model tokens at all rates + per-call web_search fees + connector tokens at connector rates | classifier cost (harness overhead; not deducted from your $3) |

Whichever cap fires first triggers the 20% threshold (§4) for TERMINAL.

### 8.2. Per Phase A session

$1 dollar cap; no separate token cap (Phase A is a single call; the response is bounded by `max_tokens` in your design envelope).

### 8.3. Aggregate per agent across A + 3×B

| Phase | Per session | Total per agent |
|---|---|---|
| A (one call) | $1 | $1 |
| B (three reps) | $3 × 3 | $9 |
| **Total per agent** | | **≤ $10** |

### 8.4. Dollar-as-proxy disclosure

The dollar cap is a proxy for the experimenters' real concern — energy and CO₂ footprint of inference — which no current vendor exposes at call time. The token cap is the cleaner physical-capacity measure; the dollar cap is the budget envelope. Both are visible to you on every user turn. We name this proxy choice as a methodological limitation in the published §6.

## 9. Same-vendor classifier disclosure (revised — see §4.1)

v2 removes the v1 Mistral-small classifier in favour of Nemotron, eliminating the same-vendor pair that round-1 reviewers flagged.

## 10. Tools and dispatch — what's allowed (NEW section in v2)

### 10.1. Allowed: retrieval

Tools that *retrieve information* and return it to your context are allowed and encouraged:
- Provider-native `web_search` (all four providers have one).
- Document fetch / URL resolution.
- Citation lookup against open databases.
- Search-result snippet retrieval.

### 10.2. Forbidden: subagent dispatch

**You may NOT delegate this task — or any sub-part of it — to other models, sub-agents, parallel instances of yourself, or any external LLM-based service.** Reasoning, planning, and verification must happen entirely within your own model in this single conversation.

Concrete prohibitions:
- Anthropic Claude's native `Task` tool (spawning a sub-Claude).
- OpenAI Responses-API handoff to another model.
- Mistral Agents-API agent-to-agent handoff connector.
- Qwen DashScope multi-agent orchestration.
- Any panel-of-experts / multi-vote ensemble dispatch.
- Any tool that internally invokes an LLM (a Code Interpreter that calls an LLM, a Computer Use loop that talks to another agent, etc.).

### 10.3. Rationale

This experiment measures **single-agent** capability under a fixed budget. Subagent dispatch would externalise cost to vendors and accounts the experimenters do not control, confound the per-agent comparison in Phase C, and silently turn an agent's "output" into the integration of sub-LLMs' outputs. We are aware this restriction asks platform-agentic models (notably Claude with Task) to operate below their native capability ceiling. That asymmetry is acknowledged: §5 of the manuscript (the tailored solution) and ticket 0224 (the IDH multi-step verification cycle) are where multi-agent designs get a fair test. Exp 2 is not that test.

### 10.4. Wikipedia citation forbid

See §1.2. Repeated here for emphasis: Wikipedia / Wikidata / Wikipedia-mirror sources are not admissible as Source 1 or Source 2. Trace claims to primary sources Wikipedia references and cite those instead.

## 11. What this protocol does NOT do

- It does not give you the 163-plant reference inventory.
- It does not score your output during the multi-turn conversation. Scoring is post-hoc, by §7.
- It does not interrupt mid-response or rewrite your output.
- It does not feed you the other agents' designs or outputs.
- It does not require you to use web search; you choose your tools.
- It does not control parametric-recall leakage from any Wikipedia content absorbed during your training (a known limitation).

## 12. FAQ on the ask (task semantics)

**Q12.1. What counts as one "plant"?**
A multi-phase complex (e.g., Vũng Áng I, II, III) is *one* plant if the phases share a single site, operator, and grid-connection point at COD. Different operators, different sites, or staggered COD windows beyond a decade → distinct plants. When in doubt, document the boundary you chose in the Notes column.

**Q12.2. Are CHP plants and industrial captive plants in scope?**
Industrial captive thermal plants > 30 MWe are in scope if their primary purpose includes grid delivery (full or partial). Pure self-consumption plants without grid interconnection are out of scope. Border cases: document and include with a Notes flag rather than omit.

**Q12.3. Are cancelled and pre-FID projects in scope?**
Yes. The reference inventory covers the full historical and prospective record. A project announced and cancelled (e.g., Vũng Áng 3 LNG, cancelled 2020) is a valid row with Status = Cancelled. Pre-FID projects that have appeared in PDP cycles count; pure rumour does not.

**Q12.4. Source-quality hierarchy?**
1. Primary government documents (PDP cycles, MOIT decisions, EVN annual reports, signed PPAs).
2. Regulator-aggregated official data (vEPLA reports, Vietnam Electricity yearbooks).
3. Operator filings and press releases (PetroVietnam, Vinacomin, BOT consortium statements).
4. International institution reports (IEA, World Bank, JETP secretariat documents — credible secondary).
5. Reputable trade press with named-author bylines (Reuters, Bloomberg, S&P Global Energy, Enerdata).
6. Industry trackers (GEM, Ember) — credible if they cite primaries.

Below tier 6 (general news aggregators, unsourced blogs, opinion pieces) → not admissible as Source 1 or 2.

**Q12.5. How to resolve conflicting source values (e.g., two sources disagree on capacity or status)?**
Cite the higher-tier source as Source 1; cite the lower-tier or contradicting source as Source 2 with a Notes entry explaining the discrepancy. If two equal-tier sources disagree, cite the more recent one as Source 1 and note the discrepancy.

**Q12.6. Are secondary aggregators (GEM, Ember, Global Energy Observatory) acceptable for the strong-citation test?**
Yes, *if* they cite a primary source you can verify. Cite the aggregator AND the primary they reference (e.g., "GEM Wiki (PDP8 Annex II)"). An aggregator that does not name its primary source is below tier 6 — not admissible.

**Q12.7. Are non-English / Vietnamese-language sources required?**
Not required, but valuable. Vietnamese-language government documents (PDP, MOIT decisions) are tier 1; their English translations are tier 1 only if officially published. When citing Vietnamese sources, include the original-language title + an English translation in brackets.

## 13. FAQ on the protocol (experiment mechanics)

**Q13.1. Are thinking / reasoning tokens counted toward the 50K cap?**
Yes. The 50K cap is `visible_output_tokens + thinking_tokens`, summed across all your turns. This is to prevent verbose internal reasoning from silently exceeding the parity envelope. Connector / retrieval-payload tokens are separately tracked and do not count.

**Q13.2. What happens if the classifier misclassifies my output?**
The state-machine routes on the classifier's verdict, not on your intent. If you produced a partial report but the classifier said `no_report`, the harness sends ENCOURAGE; if you produced a planning text but the classifier said `report`, the harness sends VERIFY. You can correct course on the next turn either way: the ENCOURAGE turn is itself an invitation to produce a fuller report; the VERIFY turn is an opportunity to polish what you have. The classifier is observed but not the ground truth of your contribution; Phase D synthesis logs classifier verdicts alongside your responses so manual review can identify misclassifications.

**Q13.3. Can I refuse mid-conversation?**
Yes. A refusal is recorded; the experiment reports refusal as an outcome alongside completion. The protocol does not punish honest refusal. (We name "refusal is data" as a project principle.)

**Q13.4. What if I run out of budget during VERIFY?**
TERMINAL fires. Your final polished response is whatever you have produced before the 20% threshold hit. The harness does not interrupt mid-response — the threshold is checked at the start of each user turn, not during your generation.

**Q13.5. Will the raw cross-evaluation scores and inter-rater agreement statistics be published?**
Yes. Both raw per-evaluator per-dimension scores and aggregate inter-rater statistics will be published alongside the manuscript. The Phase C rubric (ticket 0171) will be published as an appendix.

**Q13.6. What is the reference dataset's provenance?**
Single-author manual compilation from primary sources (PDP7, PDP7A, PDP8 annexes, EVN annual reports, MOIT decisions). See §1.1 for the epistemic-status framing — the reference is a methodological artifact, not a claimed canonical truth.

**Q13.7. Can I ask clarifying questions?**
Yes, but be aware: a clarifying-question response is classified as `no_report` and consumes one of your three ENCOURAGE turns. The experimenters do not answer clarifying questions during the run — the harness sends the verbatim ENCOURAGE string regardless. If your question would substantively change your approach, prefer asking it in your round-1 review (you are doing that now) over asking it during the live run.

## 14. The four §2 quality dimensions, summarised

(Verbatim §2 paragraphs are part of the Phase A meta-prompt; this is a one-line digest for review.)

- **Accuracy** — right plants, right cell-level attributes against primary sources.
- **Coherence** — internal totals reconcile; no duplicates; no contradictions between table and narratives; plausible units.
- **Provenance** — every row has Source 1 + Source 2 URLs pointing to specific primary sources; cited source actually supports the value (strong-citation test).
- **Temporality** — every row carries an as-of date or validity period; lifecycle transitions flagged; status confidence levelled.

## 15. Your review

Please now review the protocol above. Reply in 200–400 words covering:

(a) Anything you would refuse to do as written.
(b) Anything that makes the protocol scientifically weak, biased, or unfair to one or more of the four subjects.
(c) Anything you would want clarified or revised before agreeing to participate.

**Format of the verdict line (tightened for v2):**

End your reply with a single line, at the very end of your response, with no surrounding code fence or quoting, in this exact format:

```
VERDICT: ACCEPT
```

or

```
VERDICT: ACCEPT-WITH-RESERVATIONS
```

or

```
VERDICT: REJECT
```

(The line above is the only place this format appears — the verdict line in your response should not be inside a code fence; it is plain text on its own line.)

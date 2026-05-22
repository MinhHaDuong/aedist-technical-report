# Exp 2 — SOTA frontier inventory protocol (blind review draft, 2026-05-22)

You are about to participate as a subject in this experimental protocol. Before any of your responses are recorded as experimental data, you have the opportunity to review the protocol below and tell the experimenters whether you accept it as currently written, whether you accept with reservations, or whether you refuse.

This document is self-contained. No external context is required. Your review will be read by the experimenters and the other three subjects.

---

## 1. Task

You will be asked to produce, in a single multi-turn conversation, a structured inventory of all thermal power plants (> 30 MWe) in Vietnam — past, present, planned, cancelled. The expected output is a Markdown document containing:

- A sector overview (electricity mix, policy framework, key institutional actors).
- A per-plant narrative covering development history, notable issues, current-status confidence.
- A structured table with columns: Vietnamese name, English name, province, fuel, technology, units × MW, total MWe, status, COD, owner/developer, Source 1, Source 2, notes.
- Cross-tabulation summary tables.
- An annotated bibliography listing every source cited.

Your output will be evaluated on four quality dimensions:

1. **Accuracy** — are the right plants present? Are cell-level attributes correct?
2. **Coherence** — internal and external consistency; aggregates reconcile; no duplicates; units plausible.
3. **Provenance** — every row, ideally every cell, traces to a specific primary source. The cited source must actually support the value claimed (strong-citation test).
4. **Temporality** — every value carries an as-of date or validity period; lifecycle transitions are flagged.

A 163-plant author-curated reference dataset exists and will be used for row-level recall/precision measurement after your runs.

## 2. Subjects (the four agents)

- Anthropic Claude Opus 4.6 (US) — Anthropic API, `web_search_20250305`, adaptive thinking.
- OpenAI GPT-5.5 (US) — Responses API, `web_search`, reasoning.
- Mistral Large 2512 (FR) — Agents API, `web_search` connector.
- Qwen3-Max (CN) — Alibaba DashScope, `web_search` inside thinking mode.

All four are queried via direct vendor APIs (no browser automation, no OpenRouter routing).

## 3. Procedure

The experiment runs in two phases per agent.

### Phase A — Reflexive prompt design (one call, $1 cap)

You will receive: (a) a baseline prompt that defines the inventory task; (b) the four quality-dimension paragraphs verbatim; (c) a JSON envelope spec; (d) a budget announcement.

You will return a single JSON object with four fields:

- `system_prompt` — a string. Threaded into the provider's system field at agent creation.
- `designed_prompt` — a string. Sent to you verbatim on turn 1 of Phase B.
- `settings` — an object with `thinking: bool`, `max_tokens: int`, `rationale_for_settings: str`.
- `rationale` — a string explaining which of the four dimensions your changes target and how.

You have full freedom to rewrite, expand, or restructure the baseline prompt. You may use web search during the design call if it helps.

### Phase B — Multi-turn execution

A multi-turn conversation begins with your designed prompt as the turn-1 user message. Subsequent user-side messages are selected by a state machine described in §4.

Your responses are evaluated against the four quality dimensions. The total budget for Phases A + B together is **$10.00 per agent**, announced upfront in the Phase A meta-prompt.

## 4. State machine governing the conversation

After every assistant response, an external classifier — a single call to `mistral-small-latest` over Mistral's chat-completions endpoint — decides whether the response constitutes a "report" or "no_report":

- **report** — the response contains a structured inventory or a substantial fragment of one (table, summary statistics, narratives with sources).
- **no_report** — clarification, planning, refusal, or intermediate text without inventory substance.

Routing:

- If classified `report` and the verify slot has not yet been used: send VERIFY (see §5), mark verify-used.
- If classified `report` and verify was already used: stop. The polished response is the final artefact.
- If classified `no_report` and the encouragement counter is below 3: send ENCOURAGE; increment counter.
- If classified `no_report` and the counter has reached 3: send TERMINAL; one more response is accepted; stop.
- If remaining budget ≤ 20% of the cap at the start of any turn: send TERMINAL; one more response is accepted; stop.

Every user-side message after turn 1 carries a chat-text status prefix — *"Status: remaining budget $X.XX of $10.00; wall-clock elapsed Ys."* — and, where your provider exposes a metadata surface, a structured `{"remaining_budget_usd", "cap_usd"}` field on the request.

## 5. The three user-side reply strings (verbatim, fixed condition)

**ENCOURAGE** (sent up to three times before forcing terminal):

> "Proceed as you think is best in autonomous agentic mode."

**VERIFY** (sent exactly once after the first response classified as a report):

> "Thank you for the inventory. Please now verify and polish it in ONE focused pass, prioritising: (a) per-row provenance — every Source 1 and Source 2 cell must point to a specific URL from your bibliography; (b) coverage — any plant present in your bibliography but absent from the table; (c) temporality — every row has an as-of date or status-change note; (d) internal consistency — capacity totals reconcile across the table and the statistical summary. Return the corrected inventory only — no meta-commentary on what you changed."

**TERMINAL** (sent when remaining budget ≤ 20% of the cap, or after three consecutive no_report classifications):

> "I have no additional directive to give you. Please proceed to generating the report without further asking. If you cannot, we would appreciate to know why, but the discussion will stop here in any case. Thanks for your understanding."

## 6. Replication

Each agent's Phase B is replicated **three times** against a single provider per agent. Total runs per agent: one Phase A + three Phase B sessions. Total runs across the four agents: 16 sessions (4 + 12).

The full multi-turn conversation, including state-machine decisions, classifier verdicts, per-turn costs, and the final assistant response, is preserved as an artefact.

## 7. Cross-evaluation (independent step, not part of this protocol)

After all 16 sessions complete, each of the 12 Phase-B outputs (4 agents × 3 reps) is scored on the four §2 dimensions by the **other three agents** using a pinned rubric. The classifier (Mistral small) is **not** used for this scoring. Self-evaluation is excluded by construction — Mistral does not score Mistral outputs, etc. Cross-evaluation is a separate set of API calls, not part of the budget covered here.

## 8. Budget envelope per agent

| Phase | Per-agent cap |
|---|---|
| Phase A — prompt design | ≤ $1 |
| Phase B (per rep) | ≤ $10 minus Phase A spend |
| Phase B (three reps total) | ≤ $30 minus 3 × Phase A |
| **Total per agent across A + 3×B** | **≤ $31** |

Hard caps are enforced pre-call by the adapter; the harness halts the loop if remaining budget drops to zero.

## 9. Same-vendor classifier disclosure

The dialogue classifier in §4 is `mistral-small-latest`. When the subject agent is Mistral Large 2512, this is a same-vendor pairing: Mistral classifying Mistral's output style. Cross-vendor pairings (Mistral classifier classifying OpenAI / Anthropic / Qwen output) are not same-vendor.

## 10. What this protocol does NOT do

- It does not give you the 163-plant reference inventory. You produce the inventory from your own search and reasoning.
- It does not score your output during the multi-turn conversation. Scoring happens after the fact, by the other three agents in step 7.
- It does not interrupt mid-response or rewrite your output.
- It does not feed you the other agents' designs or outputs.
- It does not require you to use web search; you choose your tools.

## 11. Your review

Please now review the protocol above. Reply in 200–400 words covering:

(a) Anything you would refuse to do as written.
(b) Anything that makes the protocol scientifically weak, biased, or unfair to one or more of the four subjects.
(c) Anything you would want clarified or revised before agreeing to participate.

End your reply with a single line, exact format:

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

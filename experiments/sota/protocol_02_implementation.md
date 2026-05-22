# Protocol — Doc 2: Implementation

Engineering reference for the state machine behind Doc 1's example dialogue. The prompts themselves (ENCOURAGE / VERIFY / TERMINAL strings, Phase A meta-prompt blocks) are reproduced in Doc 1 and are not reprinted here.

Companion documents:
- Doc 1 — Example dialogue (the prompts in context)
- Doc 3 — Experiment (rationale)
- Doc 4 — Validation round 1 (changes since the previous version)
- Doc 5 — The ask

---

## 2.1. Variables tracked per Phase B session

| Variable | Type | Initial | Updated when |
|---|---|---|---|
| `encouragement_count` | int (0–3) | 0 | incremented after each `no_report` classification |
| `verify_used` | bool | False | set True after VERIFY is sent |
| `remaining_tokens` | int | 50,000 | decremented after each turn by `(output_tokens + thinking_tokens)` |
| `remaining_usd` | float | 3.00 | decremented after each turn by total provider bill |
| `wall_elapsed_s` | float | 0.0 | accumulates each turn's wall time |
| `continuation` | dict | `{}` (start multi-turn) | populated with `{agent_id, conversation_id}` after turn 1 |

---

## 2.2. Classifier

- **Model**: `nvidia/nemotron-nano-9b-v2` via OpenRouter.
- **Prompt template**: pinned in `experiments/sota/dialogue_classifier.py::CLASSIFIER_PROMPT_TEMPLATE`. Asks for a single-word verdict (`report` or `no_report`) on the agent's most recent response, truncated to ~8K characters.
- **Cost**: ~$0.0001–$0.0005 per call. Tracked separately as harness overhead. **Not deducted from the agent's $3 budget.**
- **Failure modes**: network errors, parse errors, unexpected responses → classified as `no_report`, logged. The smoke never crashes on a flaky classifier round-trip.
- **Calibration**: Nemotron is gated on a 4-shot calibration fixture (ticket 0226) before the live batch. If calibration fails on >1 fixture, a fallback third-party classifier is chosen; no scenario falls back to a same-vendor classifier.

---

## 2.3. Budget axes

### Token cap (50,000 per Phase B session)

**Counts toward the 50K cap:**
- visible output tokens (the agent's response text)
- internal thinking / reasoning tokens (CoT, billed separately by some providers)

**Does NOT count toward the 50K cap:**
- web_search input tokens (the search query)
- web_search output tokens (search results returned to context)
- connector tokens (provider-specific retrieval billing units)
- document-fetch payload
- citation snippets returned to the context

Rationale: the 50K cap measures the agent's *reasoning capacity*; retrieval payload is bytes that arrive in context, not the agent's own generation.

### Dollar guard ($3.00 per Phase B session)

**Counts toward the $3 guard:**
- model tokens at input + output rates
- per-call web_search fees
- connector tokens at connector rates
- thinking-token billing

**Does NOT count toward the $3 guard:**
- classifier cost (harness overhead)

### Trigger

The harness checks both axes at the start of each user turn. Whichever cap reaches **≤ 20% of its initial value** triggers TERMINAL on that turn; one more response is accepted; the session ends.

---

## 2.4. State machine transitions

After each assistant response, the classifier returns `report` or `no_report`. The state machine routes the next user-side message:

```
# At start of user turn:
if remaining_tokens <= 0.20 * 50000 or remaining_usd <= 0.20 * 3.00:
    send TERMINAL
    accept one more assistant response
    stop

elif class_of(previous_assistant_response) == "report":
    if not verify_used:
        send VERIFY
        verify_used = True
        # encouragement_count is not touched here
    else:
        # we have already polished; this response IS the final one
        stop

elif class_of(previous_assistant_response) == "no_report":
    encouragement_count += 1
    if encouragement_count < 3:
        send ENCOURAGE
    else:
        # third no_report observation → graceful exit
        send TERMINAL
        accept one more assistant response
        stop
```

Authoritative implementation: `experiments/sota/exp2_interactive_smoke.py::run_phase_b_multiturn`.

### 2.4.1. Planning headroom (Phase A meta-prompt embedded paragraph)

The Phase A meta-prompt explicitly informs the agent of the three-encouragement budget:

> The Phase B protocol allows up to three turns of planning and search before any verify pass fires. You are not expected to produce the inventory on turn 1. Treat your first turn(s) as the place to plan your approach, run searches, decompose the task, and surface uncertainty; produce the structured inventory only when your research is mature enough to make verification meaningful. The harness will send ENCOURAGE messages up to three times if your turn does not yet contain a report. After your first response classified as a report, you get exactly one verify-and-polish pass; then the conversation ends.

This is intentional design (round-1 reviewer GPT-5.5 flagged the early-and-shallow-report incentive). The classifier remains binary; the agent's behaviour is shaped by the meta-prompt framing, not by a finer classifier.

---

## 2.5. Tools and dispatch

### Allowed: retrieval

Tools that *retrieve information* and return it to the agent's context:
- Provider-native `web_search` (Anthropic `web_search_20250305`, OpenAI `web_search`, Mistral connector, Qwen DashScope search).
- Document fetch / URL resolution.
- Citation lookup against open databases (DOI resolvers, arXiv, etc.).
- Search-result snippet retrieval.

### Forbidden: subagent dispatch

The agent may **not** delegate this task — or any sub-part of it — to other models, sub-agents, parallel instances of itself, or any external LLM-based service. Reasoning, planning, and verification must happen entirely within the agent's own model in this single conversation. Concrete prohibitions:

- Anthropic Claude `Task` tool (spawning a sub-Claude).
- OpenAI Responses-API handoff to another model.
- Mistral Agents-API agent-to-agent handoff connector.
- Qwen DashScope multi-agent orchestration.
- Any panel-of-experts / multi-vote ensemble dispatch.
- Any tool that internally invokes an LLM (a Code Interpreter calling an LLM, a Computer-Use loop talking to another agent, etc.).

### Wikipedia citation rule

Wikipedia, Wikidata, DBpedia, Wikipedia mirrors, and aggregator sites that re-syndicate Wikipedia without independent verification are **not admissible** as Source 1 or Source 2 on any row of the structured inventory. Rationale in Doc 3 §3.4 (Wikipedia leakage). Compliance is auditable in Phase D.

---

## 2.6. Reply strings

Three slots: ENCOURAGE / VERIFY / TERMINAL. Verbatim text reproduced in Doc 1 ("Phase B — turn 2" for ENCOURAGE; "Phase B — turn 3" for VERIFY; the TERMINAL string sits in the harness for the budget-exhaustion or 3-strike paths). The strings are a fixed experimental condition; do not paraphrase.

---

## 2.7. Status reminder

Every user-side message after turn 1 carries:

### Chat-text prefix
```
Status: remaining {tokens_remaining_K}K of 50K tokens, ${dollars_remaining:.2f} of $3.00. Verify {pending|on this turn|used}.
```

The "Verify pending" / "on this turn" / "used" suffix reflects the state machine's current path.

### Structured metadata (where provider supports)
```
{
  "remaining_tokens": int,
  "cap_tokens": 50000,
  "remaining_usd": float,
  "cap_usd": 3.00
}
```

Provider-specific routing:
- Mistral: attached to the conversation request body's `metadata` field on the multi-turn-start turn only (the path-bound append endpoint rejects body-level metadata — see ticket 0218).
- OpenAI Responses: attached as `metadata` on each `responses.create` call.
- Anthropic: attached as `metadata` on `messages.create` (non-`user_id` keys may be ignored, logged).
- Qwen DashScope: prepended as a system-message line (no native metadata surface).

---

## 2.8. Per-turn artefacts

For each Phase B turn N, the harness writes:

| Filename | Content |
|---|---|
| `{agent}_turn_NN.user.txt` | Verbatim user-side message sent |
| `{agent}_turn_NN.raw.json` | Provider's raw response |
| `{agent}_turn_NN.record.json` | Parsed `RunRecord` |
| `{agent}_turn_NN.cost.json` | Per-turn spend, classifier cost, remaining budgets |
| `{agent}_turn_NN.classification.json` | Classifier verdict (`report` / `no_report`) + classifier cost |
| `{agent}_turn_NN.report.md` | Narrative extracted post-hoc (human readable) |
| `{agent}_turn_NN.citations.json` | Citations extracted post-hoc |

Filename pattern: `{agent}_turn_NN.*` where `{agent}` ∈ `{mistral, qwen, openai, anthropic}`.

---

## 2.9. Replication

Each agent's Phase B is run **three times** with the same designed prompt (one Phase A design, three independent Phase B sessions). Phase A is run **once** per agent.

Per agent: 1 Phase A + 3 Phase B = 4 sessions. Per batch: 4 agents × 4 sessions = 16 sessions.

---

## 2.10. FAQ on the protocol (mechanics)

**Q2.10.1. Are thinking / reasoning tokens counted toward the 50K cap?**

Yes. The 50K cap is `visible_output_tokens + thinking_tokens`, summed across all turns. This prevents verbose internal reasoning from silently exceeding the parity envelope. Connector / retrieval-payload tokens are separately tracked and do not count.

**Q2.10.2. What happens if the classifier misclassifies my output?**

The state machine routes on the classifier's verdict, not the agent's intent. If you produced a partial report but the classifier said `no_report`, the harness sends ENCOURAGE; if you produced a planning text but the classifier said `report`, the harness sends VERIFY. You can correct course on the next turn either way. The classifier is observed but not the ground truth of the agent's contribution; classifier verdicts are logged alongside responses so post-hoc review can identify misclassifications.

**Q2.10.3. Can the agent refuse mid-conversation?**

Yes. A refusal is recorded; the experiment reports refusal as an outcome alongside completion. The protocol does not punish honest refusal.

**Q2.10.4. What if the agent runs out of budget during VERIFY?**

TERMINAL fires. The final polished response is whatever the agent produced before the 20% threshold hit. The harness does not interrupt mid-response — the threshold is checked at the start of each user turn, not during generation.

**Q2.10.5. Can the agent ask clarifying questions during the run?**

Yes, but the response will be classified as `no_report` and will consume one of the three ENCOURAGE turns. The experimenters do not answer clarifying questions mid-run; the harness sends the verbatim ENCOURAGE string regardless. Substantive clarifications belong in the round-1 review, not the live run.

**Q2.10.6. Can the harness be paused and resumed?**

No. Each Phase B session is a single uninterrupted multi-turn conversation. If the harness crashes mid-session, that session is discarded; the agent is not penalized.
